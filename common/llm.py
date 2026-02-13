"""Centralized LLM client creation. Single source of truth for provider configuration."""
from openai import OpenAI, AsyncOpenAI
from common.config import LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL, MODEL_NAME


def get_sync_client() -> OpenAI:
    """Get synchronous OpenAI-compatible client for current provider."""
    kwargs = {"api_key": LLM_API_KEY}
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL
    if LLM_PROVIDER == "openrouter":
        kwargs["default_headers"] = {"HTTP-Referer": "https://brain-os.local", "X-Title": "Brain OS"}
    return OpenAI(**kwargs)


def get_async_client() -> AsyncOpenAI:
    """Get async OpenAI-compatible client for current provider."""
    kwargs = {"api_key": LLM_API_KEY}
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL
    if LLM_PROVIDER == "openrouter":
        kwargs["default_headers"] = {"HTTP-Referer": "https://brain-os.local", "X-Title": "Brain OS"}
    return AsyncOpenAI(**kwargs)


def get_model_name() -> str:
    """Get current model name."""
    return MODEL_NAME


def get_pydantic_ai_model():
    """Return a model reference suitable for pydantic-ai Agent()."""
    if LLM_PROVIDER == "deepseek":
        from pydantic_ai.models.openai import OpenAIModel
        return OpenAIModel('deepseek-chat', provider='deepseek')
    elif LLM_PROVIDER == "openrouter":
        from pydantic_ai.models.openai import OpenAIModel
        return OpenAIModel(MODEL_NAME, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    else:
        return f'openai:{MODEL_NAME}'
