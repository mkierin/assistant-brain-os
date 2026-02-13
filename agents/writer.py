from pydantic_ai import Agent, RunContext
from common.contracts import AgentResponse
from common.database import db
from common.llm import get_pydantic_ai_model

model = get_pydantic_ai_model()

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
        if isinstance(payload, str):
            payload = {"text": payload}
        content = payload.get("text", payload.get("content", ""))
        format_type = payload.get("format", "general")

        try:
            prompt = f"Format this content as a {format_type}: {content}"
            if "research_data" in payload:
                prompt += f"\n\nUse this research data: {payload['research_data']}"

            # Include conversation context for follow-ups
            conv = payload.get("conversation_history", [])
            if conv:
                ctx_lines = [f"{'User' if m.get('sender') == 'user' else 'Bot'}: {m.get('message', '')}" for m in conv[-4:]]
                prompt = f"Recent conversation:\n" + "\n".join(ctx_lines) + f"\n\nCurrent request: {prompt}"

            result = await writer_agent.run(prompt)

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


async def execute(payload: dict) -> AgentResponse:
    """Module-level execute for worker compatibility."""
    return await Writer().execute(payload)
