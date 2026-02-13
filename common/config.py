import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")  # Optional
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/brain.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")

TASK_QUEUE = "task_queue"
MAX_RETRIES = 3

# LLM provider configuration
if LLM_PROVIDER == "deepseek":
    LLM_BASE_URL = "https://api.deepseek.com"
    LLM_API_KEY = DEEPSEEK_API_KEY
    MODEL_NAME = "deepseek-chat"
elif LLM_PROVIDER == "openrouter":
    LLM_BASE_URL = "https://openrouter.ai/api/v1"
    LLM_API_KEY = OPENROUTER_API_KEY
    MODEL_NAME = OPENROUTER_MODEL
else:  # openai
    LLM_BASE_URL = None
    LLM_API_KEY = OPENAI_API_KEY
    MODEL_NAME = "gpt-4o-mini"

# Coding agent configuration
SKILLS_DIR = os.getenv("SKILLS_DIR", "skills")
CODER_OUTPUT_DIR = os.getenv("CODER_OUTPUT_DIR", "output/projects")
CODER_MODEL = os.getenv("CODER_MODEL", "gpt-4o")
