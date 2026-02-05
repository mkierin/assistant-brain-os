from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import KnowledgeEntry, AgentResponse
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel
from typing import List
import uuid

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

# Use str output for DeepSeek compatibility (no structured outputs)
archivist_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You're helping a friend find stuff in their notes. Be casual and helpful.

When they search for something:
- Find the most relevant stuff
- Keep it SHORT - just the good bits
- Sound natural, like texting

Response style:
"Found 3 notes about that:
- First one talks about X
- Second mentions Y
- This one from last week covers Z"

NO bold text (**), NO formal language. Just friendly and quick."""
)

@archivist_agent.tool
async def save_knowledge(ctx: RunContext[None], text: str, tags: List[str], source: str) -> str:
    entry = KnowledgeEntry(
        text=text,
        tags=tags,
        source=source,
        embedding_id=str(uuid.uuid4())
    )
    db.add_knowledge(entry)
    return f"Knowledge saved with tags: {', '.join(tags)}"

@archivist_agent.tool
async def search_knowledge(ctx: RunContext[None], query: str) -> str:
    results = db.search_knowledge(query)
    if not results['documents'][0]:
        return "No relevant knowledge found."
    
    context = "\n".join([f"- {doc}" for doc in results['documents'][0]])
    return f"Relevant knowledge found:\n{context}"

class Archivist:
    async def execute(self, payload: dict) -> AgentResponse:
        action = payload.get("action", "save")
        text = payload.get("text", "")

        try:
            if action == "save":
                prompt = f"Save this knowledge: {text}. Source: {payload.get('source', 'unknown')}"
            else:
                prompt = f"Search for: {text}"

            result = await archivist_agent.run(prompt)

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
