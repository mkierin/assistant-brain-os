# 🤖 Agent System Documentation

**Version**: 3.0 (Updated 2026-02-05)

Complete guide to all agents in the Assistant Brain OS system.

---

## Overview

The Assistant Brain OS uses a **multi-agent architecture** where specialized AI agents handle different types of tasks. All agents are built using **PydanticAI** and can use tools to interact with external systems.

### Agent Philosophy

- **Specialization**: Each agent has a specific domain of expertise
- **Tool-based**: Agents use tools (functions) to perform actions
- **LLM-powered**: Agents use language models for reasoning
- **Composable**: Agents can chain together for complex workflows
- **Self-healing**: Failed tasks automatically trigger rescue agent

---

## Agent Catalog

### 1. 💾 Content Saver Agent

**File**: `agents/content_saver.py`
**Purpose**: Extract and save content from various sources

#### Capabilities

##### YouTube Videos 🎥
- **Free transcript extraction** using `youtube-transcript-api`
- **Metadata extraction** using `yt-dlp` (title, channel, duration, date)
- **AI summarization** with DeepSeek:
  - TL;DR (2-3 sentences)
  - Key Points (5-7 bullets)
  - Main Concepts
  - Notable Quotes
  - Suggested Tags
- **Chapter detection** from video description
- **Timestamp links** for navigation
- **Cost**: $0.01-0.02 per video (LLM only)
- **Success rate**: 90%+ (videos with captions)

##### Web Articles 🌐
- Full content extraction with Playwright
- JavaScript rendering support
- Metadata extraction (author, date, tags)
- Auto-summarization

##### Twitter/X 🐦
- Tweet extraction
- Thread detection and assembly
- User metadata
- Link preservation

##### Plain Notes 📝
- Direct text storage
- Auto-tagging with AI
- Markdown formatting
- Link detection

#### Tools

```python
@content_saver_agent.tool
async def extract_youtube_video(ctx: RunContext[None], url: str) -> str:
    """
    Extract transcript and metadata from YouTube video.
    Returns formatted content with summary, chapters, and timestamps.
    """

@content_saver_agent.tool
async def extract_tweet(ctx: RunContext[None], url: str) -> str:
    """Extract and format tweet content with metadata."""

@content_saver_agent.tool
async def extract_webpage(ctx: RunContext[None], url: str) -> str:
    """Extract full webpage content using Playwright."""

@content_saver_agent.tool
async def save_to_knowledge_graph(ctx: RunContext[None],
                                  title: str,
                                  content: str,
                                  tags: List[str]) -> str:
    """
    Save to knowledge graph with Obsidian-style features:
    - Parse [[bidirectional links]]
    - Parse #tag/hierarchy
    - Link to daily note
    - Create embeddings with context
    """

@content_saver_agent.tool
async def get_graph_stats(ctx: RunContext[None]) -> str:
    """Get statistics about the knowledge graph."""
```

#### Usage Examples

```
User: "https://youtube.com/watch?v=abc123"
→ Extracts transcript, summarizes, saves with tags
→ Returns: Summary + key points + chapters + full transcript

User: "https://twitter.com/user/status/123"
→ Extracts tweet content and metadata
→ Saves to knowledge graph with #twitter tag

User: "Remember that machine learning is about pattern recognition"
→ Saves as plain note
→ Auto-tags with #machine-learning #concepts
```

---

### 2. 📚 Archivist Agent

**File**: `agents/archivist.py`
**Purpose**: Search and retrieve from knowledge base

#### Capabilities

##### Advanced Search Methods

1. **Semantic Search**: Vector similarity using embeddings
2. **Hybrid Search** (NEW): Combines BM25 keyword + semantic
   - Configurable weights (default: 30% keyword, 70% semantic)
   - Best of both worlds: exact matches + conceptual similarity
3. **Contextual Retrieval** (NEW): Enhanced embeddings
   - Format: `[Document: Title | Topics: tags] content`
   - Better semantic understanding
4. **Metadata Filtering** (NEW): Filter by:
   - Tags (hierarchical)
   - Date range
   - Content type (youtube, article, note, etc.)
   - Source (telegram, web, etc.)

##### Obsidian-Style Features

- **Backlinks**: Show all notes that reference a concept
- **Tag Hierarchy**: Search `#ai` finds `#ai/ml/nlp` too
- **Daily Notes**: Retrieve by date (YYYY-MM-DD)
- **Graph Traversal**: Follow links between notes

#### Tools

```python
@archivist_agent.tool
async def semantic_search(ctx: RunContext[None],
                         query: str,
                         limit: int = 5) -> str:
    """Pure vector similarity search."""

@archivist_agent.tool
async def hybrid_search(ctx: RunContext[None],
                       query: str,
                       limit: int = 5,
                       keyword_weight: float = 0.3,
                       semantic_weight: float = 0.7) -> str:
    """
    Hybrid search combining BM25 and semantic.
    Best for queries that need both exact matches and conceptual similarity.
    """

@archivist_agent.tool
async def search_with_filters(ctx: RunContext[None],
                              query: str,
                              tags: Optional[List[str]] = None,
                              date_from: Optional[str] = None,
                              date_to: Optional[str] = None,
                              content_type: Optional[str] = None) -> str:
    """
    Advanced search with metadata filtering.
    Example: Find Python videos from last month
    """

@archivist_agent.tool
async def get_backlinks(ctx: RunContext[None], note_title: str) -> str:
    """Get all notes that link to this note (Obsidian-style)."""

@archivist_agent.tool
async def get_by_tag_hierarchy(ctx: RunContext[None], tag: str) -> str:
    """
    Get notes by tag, including child tags.
    Example: #ai returns #ai/ml and #ai/robotics notes too
    """

@archivist_agent.tool
async def get_daily_note(ctx: RunContext[None], date: str = None) -> str:
    """Retrieve daily note (defaults to today)."""
```

#### Usage Examples

```
User: "Find videos about transformers"
→ Hybrid search with content_type=youtube
→ Returns: Ranked results with relevance scores

User: "What notes reference the attention mechanism?"
→ get_backlinks("Attention Mechanism")
→ Returns: All notes with [[Attention Mechanism]]

User: "Show me Python notes from January"
→ search_with_filters(tags=["python"], date_from="2026-01-01")
→ Returns: Filtered results

User: "What did I learn today?"
→ get_daily_note()
→ Returns: Today's daily note with all linked notes
```

---

### 3. 🔬 Researcher Agent

**File**: `agents/researcher.py`
**Purpose**: Deep web research with multi-source aggregation

#### Capabilities

- **Multi-source search**: Tavily, DuckDuckGo, Brave
- **Intelligent source selection**: Chooses best sources for query
- **Web page extraction**: Full content with Playwright
- **Citation tracking**: Maintains source attribution
- **Synthesis**: Combines findings from multiple sources
- **Knowledge base integration**: Searches internal KB first

#### Tools

```python
@researcher_agent.tool
async def web_search(ctx: RunContext[None],
                    query: str,
                    num_results: int = 5) -> str:
    """Multi-provider web search with result synthesis."""

@researcher_agent.tool
async def fetch_webpage(ctx: RunContext[None], url: str) -> str:
    """Extract full content from webpage."""

@researcher_agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str) -> str:
    """Search internal knowledge base before web."""

@researcher_agent.tool
async def synthesize_findings(ctx: RunContext[None],
                              sources: List[Dict]) -> str:
    """Synthesize information from multiple sources with citations."""
```

#### Usage Examples

```
User: "Research the latest developments in LLMs"
→ Searches KB + web
→ Fetches relevant pages
→ Synthesizes findings
→ Returns: Comprehensive report with citations

User: "What are the best practices for prompt engineering?"
→ Multi-source search
→ Combines academic papers, blog posts, documentation
→ Returns: Synthesized guide with sources
```

---

### 4. ✍️ Writer Agent

**File**: `agents/writer.py`
**Purpose**: Content creation and formatting

#### Capabilities

- **Draft generation**: Create content from prompts
- **Content editing**: Refine and improve existing text
- **Markdown formatting**: Structure content properly
- **Auto-tagging**: Add relevant #tags
- **Auto-linking**: Add [[note references]]
- **Context retrieval**: Pull relevant notes for context

#### Tools

```python
@writer_agent.tool
async def create_draft(ctx: RunContext[None],
                      topic: str,
                      style: str = "informative") -> str:
    """Generate content draft on topic."""

@writer_agent.tool
async def edit_content(ctx: RunContext[None],
                      content: str,
                      instructions: str) -> str:
    """Edit and refine existing content."""

@writer_agent.tool
async def format_markdown(ctx: RunContext[None], text: str) -> str:
    """Structure content with proper markdown."""

@writer_agent.tool
async def add_metadata(ctx: RunContext[None],
                      content: str) -> str:
    """Add tags and links automatically."""
```

#### Usage Examples

```
User: "Write a blog post about transformers"
→ Retrieves related notes
→ Generates structured draft
→ Adds [[links]] to concepts
→ Returns: Formatted markdown with tags

User: "Improve this paragraph: [text]"
→ Analyzes and refines
→ Returns: Enhanced version with suggestions
```

---

### 5. 🚁 Rescue Agent (Self-Healing System)

**File**: `agents/rescue_agent.py`
**Purpose**: AI-powered failure recovery and auto-repair

#### Capabilities

##### AI Diagnosis
- Analyzes failure patterns across multiple attempts
- Identifies root causes using LLM reasoning
- Assesses auto-fix confidence (0-100%)
- Proposes specific recovery actions

##### Recovery Strategies

1. **Retry with Modification** (Confidence: 80%+)
   - Fix malformed parameters
   - Adjust timeouts/limits
   - Clean/normalize input
   - Example: Malformed URL → Clean and retry

2. **Route to Different Agent** (Confidence: 85%+)
   - Wrong agent for task type
   - Try alternative approach
   - Example: Plain text → Route to note_saver instead of content_saver

3. **Apply Code Patch** (Confidence: 90%+, USE WITH CAUTION)
   - Install missing dependencies
   - Fix obvious code bugs
   - Only if safe and reversible
   - Example: Missing package → `pip install package`

4. **Skip Step** (Confidence: 85%+)
   - Non-critical step failed
   - Continue workflow without it
   - Example: Thumbnail extraction failed → Continue

5. **Escalate to Human** (Confidence: <80%)
   - Complex issue requiring human judgment
   - Creates comprehensive PR-ready issue
   - Example: Core bug → Detailed issue report

##### PR Issue Generation

When escalating, creates detailed reports with:
- **Root Cause Analysis**: What went wrong and why
- **Reproduction Steps**: How to reproduce the issue
- **Error Logs**: Full stack traces and error messages
- **Suggested Fix**: Specific code changes to resolve
- **Impact Assessment**: Severity, frequency, users affected
- **Testing Checklist**: What to test after fixing

Issues saved to: `/tmp/rescue_issues/RESCUE-*.md`

#### Tools

```python
async def diagnose_failure(context: RescueContext) -> RescueDiagnosis:
    """
    Use LLM to analyze failure and determine recovery strategy.

    Considers:
    - Failure pattern (same error 3x? different errors?)
    - Error messages and stack traces
    - Input that caused failure
    - Agent that failed
    - Available recovery options

    Returns: Diagnosis with strategy and confidence
    """

def create_pr_issue(context: RescueContext,
                   diagnosis: RescueDiagnosis) -> PRIssueSummary:
    """
    Generate comprehensive PR-ready issue report.

    Includes:
    - Summary and root cause
    - Reproduction steps
    - AI-suggested fix with code
    - Impact assessment
    - Testing checklist
    """

async def attempt_recovery(diagnosis: RescueDiagnosis,
                          context: RescueContext) -> str:
    """
    Execute recovery actions based on diagnosis.

    Actions might include:
    - Modify job parameters
    - Change agent routing
    - Install packages (if safe)
    - Create PR issue
    """
```

#### How It Works

```
1. Task fails → Retry 1 → Retry 2 → Retry 3 → Still failing?
                                                     ↓
2. Worker dispatches rescue agent with full context:
   - All 3 failure attempts with errors
   - Stack traces
   - Input payload
   - Agent that failed
                                                     ↓
3. Rescue agent analyzes with LLM:
   - What pattern do we see?
   - What's the root cause?
   - Can we fix it safely?
   - How confident are we?
                                                     ↓
4. Decision based on confidence:
   - High (≥80%): Auto-fix and requeue
   - Low (<80%): Create PR issue and notify user
```

#### Usage Examples

```
Example 1: Auto-Fixed
User shares: "https://youtube.com/watch?v=abc&extra=params"
→ content_saver fails (malformed URL)
→ Rescue diagnoses: "URL has extra parameters"
→ Confidence: 95%
→ Action: Clean URL, retry
→ Result: ✅ Task succeeds

Example 2: PR Created
User shares: "https://youtube.com/watch?v=no_captions"
→ content_saver fails (NoTranscriptFound)
→ Rescue diagnoses: "Video has no captions, missing error handling"
→ Confidence: 65%
→ Action: Create PR issue with fix suggestion
→ Result: Developer gets detailed report
```

---

## Agent Communication

### Shared Knowledge Graph

All agents communicate via the centralized knowledge graph:

```
Content Saver → Save to KB
                    ↓
              Knowledge Graph
                    ↓
Archivist ← Search KB → Researcher ← Read KB
                    ↓
              Writer ← Retrieve context
```

### Agent Chaining

Agents can chain together for complex workflows:

```python
# Example: Research → Save → Summarize
result = await researcher_agent.run("Research topic X")
→ next_agent = "content_saver"
  → next_agent = "writer"
```

---

## Technical Implementation

### PydanticAI Pattern

All agents follow this structure:

```python
from pydantic_ai import Agent, RunContext
from common.config import get_llm_client

# Initialize agent
agent = Agent(
    model,
    output_type=str,  # DeepSeek compatibility
    system_prompt="You are a [agent type]...",
    retries=3
)

# Define tools
@agent.tool
async def tool_function(ctx: RunContext[None], param: str) -> str:
    """Tool description for LLM."""
    # Implementation
    return result

# Entry point (called by worker)
async def execute(input: str) -> AgentResponse:
    """Main execution function."""
    try:
        result = await agent.run(input)
        return AgentResponse(
            success=True,
            output=result.output
        )
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e)
        )
```

### Dynamic Loading

Worker loads agents dynamically:

```python
# worker.py
agent_module = importlib.import_module(f"agents.{agent_name}")

if hasattr(agent_module, 'execute'):
    # New pattern: module-level execute function
    execute_func = getattr(agent_module, 'execute')
    response = await execute_func(input)
else:
    # Old pattern: class-based agent
    agent_class = getattr(agent_module, agent_name.capitalize())
    agent_instance = agent_class()
    response = await agent_instance.execute(payload)
```

---

## Configuration

### Environment Variables

```bash
# LLM Provider
LLM_PROVIDER=deepseek  # or openai
MODEL_NAME=deepseek-chat

# API Keys
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...  # For Whisper only

# Database
CHROMA_PATH=./chroma_db
POSTGRES_URL=postgresql://...
REDIS_URL=redis://localhost:6379
```

### Agent-Specific Settings

Each agent can have custom settings in `.env`:

```bash
# Content Saver
YOUTUBE_MAX_TRANSCRIPT_LENGTH=50000
WEB_SCRAPING_TIMEOUT=30

# Researcher
MAX_WEB_SOURCES=5
RESEARCH_DEPTH=detailed

# Rescue Agent
RESCUE_CONFIDENCE_THRESHOLD=0.8
AUTO_FIX_ENABLED=true
```

---

## Testing Agents

### Manual Testing

```bash
# Test content_saver
python -c "
from agents.content_saver import execute
import asyncio
result = asyncio.run(execute('https://youtube.com/watch?v=abc123'))
print(result.output)
"

# Test archivist
python -c "
from agents.archivist import execute
import asyncio
result = asyncio.run(execute('search for machine learning notes'))
print(result.output)
"
```

### Unit Tests

```bash
# Run agent tests
pytest tests/test_agents.py -v

# Test specific agent
pytest tests/test_agents.py::test_content_saver -v
```

---

## Adding New Agents

To add a new agent:

1. **Create agent file**: `agents/my_agent.py`

2. **Implement agent pattern**:
```python
from pydantic_ai import Agent
from common.contracts import AgentResponse

agent = Agent(model, output_type=str, system_prompt="...")

@agent.tool
async def my_tool(ctx, param: str) -> str:
    return result

async def execute(input: str) -> AgentResponse:
    result = await agent.run(input)
    return AgentResponse(success=True, output=result.output)
```

3. **Register in routing**: Update `main.py` route_intent()

4. **Add tests**: Create `tests/test_my_agent.py`

5. **Document**: Add to this file and README.md

---

## Performance Metrics

### Agent Latency

- Content Saver (YouTube): 5-10s (transcript + LLM)
- Archivist (search): 100-300ms
- Researcher (web): 10-30s (multi-source)
- Writer (draft): 3-7s (LLM generation)
- Rescue (diagnosis): 3-5s (LLM analysis)

### Cost per Request

- Content Saver: $0.01-0.02 (LLM summary)
- Archivist: $0.001-0.002 (embeddings)
- Researcher: $0.05-0.10 (multi-source + synthesis)
- Writer: $0.02-0.05 (generation)
- Rescue: $0.02-0.03 (diagnosis)

---

## Future Agent Ideas

Potential agents to add:

- **📊 Analyst Agent**: Data analysis and visualization
- **🎨 Designer Agent**: Generate diagrams and visuals
- **📅 Planner Agent**: Task and project planning
- **🔗 Connector Agent**: Integration with external services
- **🤝 Collaborator Agent**: Multi-user coordination
- **🎓 Tutor Agent**: Interactive learning and teaching

---

**Last Updated**: 2026-02-05
**See Also**: ARCHITECTURE.md, README.md, RESCUE_SYSTEM.md
