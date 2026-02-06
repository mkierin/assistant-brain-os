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
from common.goal_tracker import GoalTracker

r = redis.from_url(REDIS_URL)
bot = Bot(token=TELEGRAM_TOKEN)

# Goal tracker singleton (lazy init)
_goal_tracker = None

def get_goal_tracker():
    global _goal_tracker
    if _goal_tracker is None:
        from common.database import db
        _goal_tracker = GoalTracker(db.conn, r)
    return _goal_tracker

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

    # Record goal for tracking
    tracker = get_goal_tracker()
    goal_type = job.payload.get("goal_type", "UNKNOWN")
    tracker.record_goal(
        job_id=str(job.id),
        user_id=str(job.payload.get("user_id", "")),
        source=job.payload.get("source", "telegram"),
        goal_type=goal_type,
        agent=job.current_agent,
        user_input=job.payload.get("text", "")[:500]
    )

    print(f"🔄 Processing Job: {job.id} | Agent: {job.current_agent} | Goal: {goal_type} | User: {job.payload.get('user_id')}")

    try:
        # Dynamically load agent
        agent_module = importlib.import_module(f"agents.{job.current_agent}")

        # Check if agent has a module-level execute function
        if hasattr(agent_module, 'execute'):
            execute_func = getattr(agent_module, 'execute')
            # Pass full payload so agents have access to user_id, source, etc.
            response: AgentResponse = await execute_func(job.payload)
        else:
            # Fallback: class-based agent
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

            # Evaluate goal fulfillment
            tracker.evaluate_and_record(
                job_id=str(job.id),
                agent_response=response,
                duration=duration,
                retry_count=job.retry_count
            )

            # Send result to the appropriate channel based on source
            user_id = job.payload.get("user_id")
            source = job.payload.get("source", "telegram")

            if user_id:
                if source == "web":
                    # Web users: push response to Redis for polling
                    web_response = json.dumps({
                        "id": str(job.id),
                        "message": response.output,
                        "sender": "bot",
                        "timestamp": datetime.now().isoformat()
                    })
                    response_key = f"web_response:{user_id}"
                    r.lpush(response_key, web_response)
                    r.expire(response_key, 3600)  # Keep for 1 hour

                    # Also store in conversation history
                    conv_key = f"web_conversation:{user_id}"
                    r.lpush(conv_key, web_response)
                    r.expire(conv_key, 86400)
                    print(f"📤 Web response queued for {user_id}")
                else:
                    # Telegram users: send message directly
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
            # Record goal as unfulfilled at max retries
            tracker.evaluate_and_record(
                job_id=str(job.id),
                agent_response=AgentResponse(success=False, output="", error=str(e)),
                duration=int(time.time() - start_time),
                retry_count=job.retry_count
            )

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
