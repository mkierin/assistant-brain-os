from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import KnowledgeEntry, AgentResponse
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', base_url='https://api.deepseek.com', api_key=DEEPSEEK_API_KEY)
else:
    model = 'openai:gpt-4o-mini'

archivist_agent = Agent(
    model,
    result_type=AgentResponse,
    system_prompt="""You are the Archivist. Your job is to store and retrieve knowledge.
When saving, ensure you extract relevant tags.
When searching, provide the most relevant context found in the brain."""
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
        
        if action == "save":
            prompt = f"Save this knowledge: {text}. Source: {payload.get('source', 'unknown')}"
        else:
            prompt = f"Search for: {text}"
            
        result = await archivist_agent.run(prompt)
        return result.data
