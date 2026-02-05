import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")  # Optional
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/brain.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")

TASK_QUEUE = "task_queue"
MAX_RETRIES = 3
