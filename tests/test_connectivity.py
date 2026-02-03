import os
import redis
import sqlite3
import asyncio
from telegram import Bot
from common.config import TELEGRAM_TOKEN, REDIS_URL, DATABASE_PATH

async def test_telegram():
    print("Testing Telegram Bot...")
    if not TELEGRAM_TOKEN:
        print("Telegram TOKEN not found in .env")
        return False
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        me = await bot.get_me()
        print(f"SUCCESS: Telegram Bot is working: @{me.username}")
        return True
    except Exception as e:
        print(f"ERROR: Telegram Bot Error: {e}")
        return False

def test_redis():
    print("Testing Redis Connection...")
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("SUCCESS: Redis is working")
        return True
    except Exception as e:
        print(f"ERROR: Redis Error: {e}")
        return False

def test_sqlite():
    print("Testing SQLite Database...")
    try:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("SELECT 1")
        conn.close()
        print("SUCCESS: SQLite is working")
        return True
    except Exception as e:
        print(f"ERROR: SQLite Error: {e}")
        return False

async def main():
    t_ok = await test_telegram()
    r_ok = test_redis()
    s_ok = test_sqlite()
    
    if all([t_ok, r_ok, s_ok]):
        print("\n🚀 All systems ready!")
    else:
        print("\n⚠️ Some systems failed. Please check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
