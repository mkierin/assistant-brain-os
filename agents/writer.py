from pydantic_ai import Agent, RunContext
from common.contracts import AgentResponse
from common.database import db
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

# Use str output for DeepSeek compatibility
writer_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You are the Writer. Your job is to format and synthesize information into high-quality content.
You can draft emails, blog posts, reports, or just format a clean response for the user.
Use the tools to fetch context from the brain if needed.
Provide well-formatted, professional content."""
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

        try:
            prompt = f"Format this content as a {format_type}: {content}"
            if "research_data" in payload:
                prompt += f"\n\nUse this research data: {payload['research_data']}"

            result = await writer_agent.run(prompt)

            # Convert string output to AgentResponse
            return AgentResponse(
                success=True,
                output=result.output,
                next_agent=None,
                data=None,
                error=None
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                output="",
                error=str(e)
            )
