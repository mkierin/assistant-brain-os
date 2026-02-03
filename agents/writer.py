from pydantic_ai import Agent, RunContext
from common.contracts import AgentResponse
from common.database import db
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', base_url='https://api.deepseek.com', api_key=DEEPSEEK_API_KEY)
else:
    model = 'openai:gpt-4o-mini'

writer_agent = Agent(
    model,
    result_type=AgentResponse,
    system_prompt="""You are the Writer. Your job is to format and synthesize information into high-quality content.
You can draft emails, blog posts, reports, or just format a clean response for the user.
Use the tools to fetch context from the brain if needed."""
)

@writer_agent.tool
async def get_context(ctx: RunContext[None], query: str) -> str:
    results = db.search_knowledge(query)
    if not results['documents'][0]:
        return "No relevant context found in the brain."
    
    context = "\n".join([f"- {doc}" for doc in results['documents'][0]])
    return f"Context found:\n{context}"

class Writer:
    async def execute(self, payload: dict) -> AgentResponse:
        content = payload.get("text", payload.get("content", ""))
        format_type = payload.get("format", "general")
        
        prompt = f"Format this content as a {format_type}: {content}"
        if "research_data" in payload:
            prompt += f"\n\nUse this research data: {payload['research_data']}"
            
        result = await writer_agent.run(prompt)
        return result.data
