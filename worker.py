import redis
import json
import asyncio
import importlib
from telegram import Bot
from common.config import REDIS_URL, TASK_QUEUE, TELEGRAM_TOKEN
from common.contracts import Job, JobStatus, AgentResponse

r = redis.from_url(REDIS_URL)
bot = Bot(token=TELEGRAM_TOKEN)

async def process_job(job_data: str):
    job_dict = json.loads(job_data)
    job = Job(**job_dict)
    job.status = JobStatus.IN_PROGRESS
    
    print(f"Processing Job: {job.id} | Agent: {job.current_agent}")
    
    try:
        # Dynamically load agent
        agent_module = importlib.import_module(f"agents.{job.current_agent}")
        agent_class_name = job.current_agent.capitalize()
        agent_class = getattr(agent_module, agent_class_name)
        agent_instance = agent_class()
        
        # Execute agent
        response: AgentResponse = await agent_instance.execute(job.payload)
        
        if response.success:
            job.status = JobStatus.COMPLETED
            job.history.append({"agent": job.current_agent, "output": response.output})
            
            # Send notification
            user_id = job.payload.get("user_id")
            if user_id:
                await bot.send_message(chat_id=user_id, text=f"✅ Task Completed!\n\n{response.output}")
                
            # Chain next agent if specified
            if response.next_agent:
                job.current_agent = response.next_agent
                job.status = JobStatus.PENDING
                r.lpush(TASK_QUEUE, job.model_dump_json())
        else:
            raise Exception(response.error or "Agent failed without error message")
            
    except Exception as e:
        print(f"Error processing job {job.id}: {str(e)}")
        job.retry_count += 1
        job.history.append({"agent": job.current_agent, "error": str(e)})
        
        if job.retry_count < job.max_retries:
            job.status = JobStatus.PENDING
            r.lpush(TASK_QUEUE, job.model_dump_json())
        else:
            job.status = JobStatus.WAITING_HUMAN
            user_id = job.payload.get("user_id")
            if user_id:
                await bot.send_message(
                    chat_id=user_id, 
                    text=f"⚠️ Task Failed after {job.max_retries} retries.\nJob ID: {job.id}\nError: {str(e)}\n\nPlease check logs or provide feedback."
                )

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
