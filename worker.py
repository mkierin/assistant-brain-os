import redis
import json
import asyncio
import importlib
import traceback
from datetime import datetime
from telegram import Bot
from telegram.error import BadRequest
from common.config import REDIS_URL, TASK_QUEUE, TELEGRAM_TOKEN
from common.contracts import Job, JobStatus, AgentResponse, FailureDetail

r = redis.from_url(REDIS_URL)
bot = Bot(token=TELEGRAM_TOKEN)

# Telegram message length limit
TELEGRAM_MAX_LENGTH = 4096

async def send_long_message(chat_id: int, text: str):
    """Send a message, splitting into chunks if it exceeds Telegram's limit"""
    if len(text) <= TELEGRAM_MAX_LENGTH:
        await bot.send_message(chat_id=chat_id, text=text)
        return

    # Split into chunks
    chunks = []
    current_chunk = ""

    # Try to split by paragraphs first
    paragraphs = text.split('\n\n')

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= TELEGRAM_MAX_LENGTH:
            current_chunk += para + '\n\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            # If single paragraph is too long, split by sentences
            if len(para) > TELEGRAM_MAX_LENGTH:
                sentences = para.split('. ')
                temp_chunk = ""
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) + 2 <= TELEGRAM_MAX_LENGTH:
                        temp_chunk += sentence + '. '
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sentence + '. '
                if temp_chunk:
                    current_chunk = temp_chunk
            else:
                current_chunk = para + '\n\n'

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Send all chunks
    for i, chunk in enumerate(chunks):
        if i == 0:
            await bot.send_message(chat_id=chat_id, text=chunk)
        else:
            await bot.send_message(chat_id=chat_id, text=f"(continued...)\n\n{chunk}")
        await asyncio.sleep(0.5)  # Small delay between messages

async def process_job(job_data: str):
    job_dict = json.loads(job_data)
    job = Job(**job_dict)
    job.status = JobStatus.IN_PROGRESS

    import time
    start_time = time.time()

    # Track active job in Redis for monitoring
    job_info = {
        "job_id": str(job.id),
        "agent": job.current_agent,
        "started": int(time.time()),
        "user_id": job.payload.get("user_id")
    }
    r.setex(f"job:processing:{job.id}", 300, json.dumps(job_info))  # Expire after 5 min

    print(f"🔄 Processing Job: {job.id} | Agent: {job.current_agent} | User: {job.payload.get('user_id')}")
    
    try:
        # Dynamically load agent
        agent_module = importlib.import_module(f"agents.{job.current_agent}")

        # Check if agent has a module-level execute function (new pattern)
        if hasattr(agent_module, 'execute'):
            # New pattern: module-level execute function
            execute_func = getattr(agent_module, 'execute')
            # Pass the text from payload
            text = job.payload.get("text", "")
            response: AgentResponse = await execute_func(text)
        else:
            # Old pattern: class-based agent
            agent_class_name = job.current_agent.capitalize()
            agent_class = getattr(agent_module, agent_class_name)
            agent_instance = agent_class()
            response: AgentResponse = await agent_instance.execute(job.payload)
        
        if response.success:
            job.status = JobStatus.COMPLETED
            job.history.append({"agent": job.current_agent, "output": response.output})

            # Calculate duration
            duration = int(time.time() - start_time)

            # Log completion
            completion_info = {
                "job_id": str(job.id),
                "agent": job.current_agent,
                "duration": duration,
                "timestamp": int(time.time())
            }
            r.setex(f"job:completed:{job.id}", 600, json.dumps(completion_info))  # Keep for 10 min

            # Remove from processing
            r.delete(f"job:processing:{job.id}")

            print(f"✅ Job {job.id} completed | Agent: {job.current_agent} | Duration: {duration}s | Output: {len(response.output)} chars")

            # Send result directly (no "Task Completed" prefix - just natural output)
            # Handles long messages by splitting into chunks
            user_id = job.payload.get("user_id")
            if user_id:
                try:
                    await send_long_message(chat_id=user_id, text=response.output)
                except Exception as send_error:
                    print(f"❌ Error sending message: {send_error}")
                    # Fallback: send truncated message
                    truncated = response.output[:TELEGRAM_MAX_LENGTH-100] + "\n\n...(message truncated - too long)"
                    await bot.send_message(chat_id=user_id, text=truncated)
                
            # Chain next agent if specified
            if response.next_agent:
                job.current_agent = response.next_agent
                job.status = JobStatus.PENDING
                r.lpush(TASK_QUEUE, job.model_dump_json())
        else:
            raise Exception(response.error or "Agent failed without error message")
            
    except Exception as e:
        # Remove from processing
        r.delete(f"job:processing:{job.id}")

        # Collect detailed failure information
        stack_trace = traceback.format_exc()
        print(f"❌ Error processing job {job.id}: {str(e)}")

        job.retry_count += 1

        # Store detailed failure info for rescue agent
        failure_detail = {
            "timestamp": datetime.now().isoformat(),
            "attempt": job.retry_count,
            "agent": job.current_agent,
            "error_message": str(e),
            "stack_trace": stack_trace,
            "input_payload": job.payload
        }
        job.history.append(failure_detail)

        if job.retry_count < job.max_retries:
            job.status = JobStatus.PENDING
            print(f"♻️  Retrying job {job.id} (attempt {job.retry_count + 1}/{job.max_retries})")
            r.lpush(TASK_QUEUE, job.model_dump_json())
        else:
            # 🚁 RESCUE MODE - Dispatch to AI-powered rescue agent
            job.status = JobStatus.WAITING_HUMAN
            print(f"🚨 Job {job.id} failed {job.max_retries} times - Dispatching Rescue Agent...")

            # Build rescue context
            rescue_context = {
                "workflow_goal": job.payload.get("text", "Unknown task"),
                "failure_history": job.history,
                "agent_code": None,  # Could read agent source code here
                "worker_logs": None  # Could include recent worker logs
            }

            # Create rescue job
            rescue_job = Job(
                current_agent="rescue_agent",
                payload={
                    "failed_job": job.model_dump(),
                    "context": rescue_context
                },
                max_retries=1  # Don't retry rescue itself
            )

            # Dispatch rescue agent
            r.lpush(TASK_QUEUE, rescue_job.model_dump_json())
            print(f"🚁 Rescue Agent dispatched for job {job.id}")

async def worker_loop():
    print("Worker started. Listening for tasks...")
    while True:
        # BLPOP blocks until an item is available
        task = r.blpop(TASK_QUEUE, timeout=5)
        if task:
            _, job_data = task
            await process_job(job_data)
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(worker_loop())
