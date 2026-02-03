import os
import asyncio
import json
import redis
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from common.config import TELEGRAM_TOKEN, OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER, REDIS_URL, TASK_QUEUE
from common.contracts import Job, JobStatus

if LLM_PROVIDER == "deepseek":
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    MODEL_NAME = "deepseek-chat"
else:
    client = OpenAI(api_key=OPENAI_API_KEY)
    MODEL_NAME = "gpt-4o-mini"

r = redis.from_url(REDIS_URL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Brain Orchestrator is online. Send me text or voice.")

async def route_intent(text: str) -> dict:
    prompt = f"""Analyze this user request and route it to the correct agent.
Available agents:
- archivist: For saving information, thoughts, or searching the brain.
- researcher: For deep research on topics, browsing the web, or finding new info.
- writer: For formatting content, drafting emails, or writing reports.

User Request: {text}

Return JSON: {{"agent": "agent_name", "payload": {{...}}}}"""
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": "You are a routing system. Return ONLY JSON."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ""
    # Always use OpenAI for Whisper regardless of LLM_PROVIDER
    whisper_client = OpenAI(api_key=OPENAI_API_KEY)
    
    if update.message.voice:
        # Handle voice
        file = await context.bot.get_file(update.message.voice.file_id)
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{update.message.voice.file_id}.ogg"
        await file.download_to_drive(file_path)
        
        with open(file_path, "rb") as audio_file:
            transcript = whisper_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        text = transcript.text
        await update.message.reply_text(f"Transcript: {text}")
        os.remove(file_path)
    else:
        text = update.message.text

    # Route intent
    routing = await route_intent(text)
    agent = routing.get("agent", "archivist")
    payload = routing.get("payload", {"text": text})
    payload["source"] = "telegram"
    payload["user_id"] = update.effective_user.id

    # Create Job
    job = Job(current_agent=agent, payload=payload)
    
    # Push to Redis
    r.lpush(TASK_QUEUE, job.model_dump_json())
    
    await update.message.reply_text(f"Job queued: {job.id}\nAgent: {agent}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))
    
    print("Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()
