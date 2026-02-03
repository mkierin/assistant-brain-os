import os
import asyncio
import redis
import httpx
from openai import OpenAI
from common.config import (
    TELEGRAM_TOKEN, 
    OPENAI_API_KEY, 
    DEEPSEEK_API_KEY, 
    LLM_PROVIDER, 
    REDIS_URL, 
    DATABASE_PATH
)

async def check_redis():
    print("🔍 Checking Redis...")
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("✅ Redis is connected.")
        return True
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False

async def check_telegram():
    print(f"🔍 Checking Telegram Bot (Token: {TELEGRAM_TOKEN[:10]}...)...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe")
            data = resp.json()
            if data.get("ok"):
                print(f"✅ Telegram Bot is valid: @{data['result']['username']}")
                return True
            else:
                print(f"❌ Telegram Bot error: {data.get('description')}")
                return False
    except Exception as e:
        print(f"❌ Telegram connection error: {e}")
        return False

async def check_llm():
    print(f"🔍 Checking LLM Provider: {LLM_PROVIDER}...")
    try:
        if LLM_PROVIDER == "deepseek":
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
            model = "deepseek-chat"
        else:
            client = OpenAI(api_key=OPENAI_API_KEY)
            model = "gpt-4o-mini"
        
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5
        )
        print(f"✅ {LLM_PROVIDER} is responding: {resp.choices[0].message.content.strip()}")
        return True
    except Exception as e:
        print(f"❌ {LLM_PROVIDER} error: {e}")
        return False

async def check_whisper():
    print("🔍 Checking OpenAI Whisper (for STT)...")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        # We just check if the key is valid by listing models or doing a tiny request if possible
        # but listing models is safer/cheaper
        client.models.list()
        print("✅ OpenAI API key is valid for Whisper.")
        return True
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return False

async def main():
    print("=== System Integrity Check ===\n")
    results = await asyncio.gather(
        check_redis(),
        check_telegram(),
        check_llm(),
        check_whisper()
    )
    
    print("\n" + "="*30)
    if all(results):
        print("🚀 ALL SYSTEMS GO!")
    else:
        print("⚠️ SOME SYSTEMS FAILED. Please check the logs above.")
    print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
