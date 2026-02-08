# 🤖 Agent System Documentation

**Version**: 4.0 (Updated 2026-02-08)

Complete guide to all agents in the Assistant Brain OS system, including the new Journal and Task Manager agents.

---

## Overview

The Assistant Brain OS uses a **multi-agent architecture** where specialized AI agents handle different types of tasks. All agents are built using **PydanticAI** and can use tools to interact with external systems.

### Agent Philosophy

- **Specialization**: Each agent has a specific domain of expertise
- **"Code decides, LLM formats"**: Deterministic logic for decisions, LLM only for synthesis/formatting
- **Zero-LLM agents**: Journal, task manager, archivist use pure regex — no LLM calls
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

### 6. 📓 Journal Agent (Zero LLM)

**File**: `agents/journal.py`
**Purpose**: Voice & text journaling with auto-linking to knowledge graph

#### Capabilities

- **Fully deterministic** — zero LLM calls
- **Prefix stripping**: Removes "journal:", "diary entry:", "daily log:", "log:", etc.
- **Topic extraction**: Keyword-based extraction, filters 60+ stop words, max 7 topics
- **Mood detection**: Regex patterns for positive (happy, productive, grateful), negative (frustrated, stressed), neutral (okay, fine, normal)
- **Title generation**: Date + first sentence, truncated to 60 chars
- **Cross-linking**: Searches existing knowledge for related notes, creates edges in knowledge graph
- **View history**: Lists last 7 entries with dates, previews, and tags

#### Voice Journal Mode

When the `voice_journal` setting is enabled (via `/settings`), **all voice messages** bypass normal routing and go directly to the journal agent. This enables hands-free diary recording.

#### Functions

```python
def _strip_journal_prefix(text: str) -> str
    """Remove 'journal:', 'diary entry:', 'daily log:', etc."""

def _extract_topics(text: str) -> List[str]
    """Extract meaningful topics/tags. No LLM. Max 7, deduped."""

def _detect_mood(text: str) -> Optional[str]
    """Simple regex mood detection: positive/negative/neutral/None."""

def _generate_title(text: str, date: str) -> str
    """Date + first sentence, truncated to 60 chars."""

def _find_related_knowledge(text: str, topics: List[str]) -> List[Dict]
    """Search existing knowledge for cross-linking."""

def _link_to_knowledge_graph(entry_id, title, content, tags, related)
    """Add journal node + create 'related-to' edges."""

def _detect_action(text: str) -> str
    """'save' or 'view' based on regex patterns."""

async def execute(payload) -> AgentResponse
    """Entry point. Routes to _handle_save or _handle_view."""
```

#### Storage

- Saved to `knowledge` table with `content_type: "journal"` in metadata
- Tags always include: `["journal", "YYYY-MM-DD", ...topics]`
- Metadata: `{content_type, date, input_source, user_id, mood}`

#### Usage Examples

```
User (voice): "Had a productive meeting about the Python migration"
→ Strips prefix, extracts topics: #meeting #python #migration
→ Detects mood: positive
→ Searches KB, finds related "Python Notes" entry
→ Creates knowledge graph edges
→ Returns: "Journal entry saved for 2026-02-08. Mood: positive. Topics: #meeting, #python, #migration. Linked to 1 related note: Python Notes"

User: "show my journal"
→ Detects action: view
→ Lists last 7 entries with dates and tags
```

---

### 7. ✅ Task Manager Agent (Zero LLM)

**File**: `agents/task_manager.py`
**Purpose**: Deterministic task/reminder CRUD with natural language dates

#### Capabilities

- **Fully deterministic** — zero LLM calls
- **Natural language dates**: "tomorrow", "next Friday", "by March 15" via `dateparser`
- **Priority detection**: urgent/asap/critical → high, no rush/someday → low, default → medium
- **Task CRUD**: Add, list, complete (by #number or keyword), delete
- **Smart completion matching**: Match by task number (#1) or keyword overlap
- **Reminder scheduler**: `check_reminders()` runs every 15 min via JobQueue
- **Auto-linking**: Tasks linked to related knowledge entries

#### Functions

```python
def _detect_action(text: str) -> str
    """Classify: 'add', 'list', 'complete', or 'delete'."""

def _extract_date_and_task(text: str) -> Tuple[due_date, reminder_at, title]
    """Parse natural language dates with dateparser. Default reminder: 9 AM."""

def _strip_task_prefix(text: str) -> str
    """Remove 'remind me to', 'todo:', 'task:', etc."""

def _extract_priority(text: str) -> str
    """Regex priority detection: high/medium/low."""

def _extract_complete_target(text: str, tasks: List) -> Optional[str]
    """Find task by #number or keyword overlap."""

def _format_task_list(tasks: List[Dict]) -> str
    """Format with due dates, overdue warnings, priority indicators."""

async def execute(payload) -> AgentResponse
    """Entry point. Routes to add/list/complete/delete handlers."""
```

#### Database Schema

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL,
    due_date TEXT,          -- YYYY-MM-DD
    reminder_at TEXT,       -- ISO datetime
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    tags TEXT DEFAULT '[]',
    linked_knowledge TEXT DEFAULT '[]',
    created_at TEXT,
    completed_at TEXT
);
```

#### Reminder Scheduler

```python
# In main.py — runs every 15 minutes
app.job_queue.run_repeating(check_reminders, interval=900, first=60)

async def check_reminders(context):
    reminders = db.get_due_reminders()
    for r in reminders:
        await context.bot.send_message(user_id, f"Reminder: {r['title']}")
        db.mark_reminder_sent(r['id'])
```

#### Usage Examples

```
User: "remind me to call John tomorrow at 3pm"
→ Strips prefix: "call John tomorrow at 3pm"
→ Parses date: tomorrow, reminder at 3pm
→ Priority: medium
→ Returns: "Task added: Call John\nDue: 2026-02-09\nReminder set: 2026-02-09T15:00:00"

User: "my tasks"
→ Lists pending tasks with due dates and overdue warnings
→ "You have 3 pending tasks:\n  1. Call John [due tomorrow]\n  2. Submit report [!!] [OVERDUE by 2 days]"

User: "done with #1"
→ Matches task #1: "Call John"
→ Returns: "Done! Completed: Call John\n2 tasks remaining."
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

### Agent Patterns

The system uses two patterns:

#### Pattern 1: Deterministic (Zero LLM) — Preferred
Used by: journal, task_manager, archivist, content_saver

```python
from common.contracts import AgentResponse
from common.database import db

async def execute(payload) -> AgentResponse:
    """Deterministic — no LLM calls."""
    if isinstance(payload, str):
        text = payload
        user_id = "default"
    else:
        text = payload.get("text", "")
        user_id = str(payload.get("user_id", "default"))

    action = _detect_action(text)  # Pure regex
    # Process deterministically, call DB directly
    return AgentResponse(success=True, output="result")
```

#### Pattern 2: LLM-Assisted
Used by: researcher, writer — LLM for formatting/synthesis only

```python
from pydantic_ai import Agent
from common.contracts import AgentResponse

agent = Agent(model, output_type=str, system_prompt="...")

async def execute(payload) -> AgentResponse:
    # Gather data deterministically first
    results = db.search_clean(query)
    # LLM only for formatting
    result = await agent.run(format_prompt(results))
    return AgentResponse(success=True, output=result.output)
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
CHROMA_PATH=data/chroma
DATABASE_PATH=data/brain.db
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
# Run all 362 tests
pytest tests/ -v

# Test specific agents
pytest tests/test_journal.py -v         # 51 journal tests
pytest tests/test_task_manager.py -v    # 61 task manager tests
pytest tests/test_bug_fixes.py -v       # Core agent tests
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

3. **Register in routing**: Add patterns to `route_deterministic()` in `main.py`

4. **Add tests**: Create `tests/test_my_agent.py`

5. **Document**: Add to this file and README.md

---

## Performance Metrics

### Agent Latency

- Content Saver (YouTube): 5-10s (transcript + LLM)
- Archivist (search): 100-300ms
- Researcher (web): 10-30s (multi-source)
- Writer (draft): 3-7s (LLM generation)
- Journal (save): < 50ms (zero LLM, deterministic)
- Task Manager (CRUD): < 20ms (zero LLM, deterministic)
- Rescue (diagnosis): 3-5s (LLM analysis)

### Cost per Request

- Content Saver: $0.01-0.02 (LLM summary)
- Archivist: $0.001-0.002 (embeddings)
- Researcher: $0.05-0.10 (multi-source + synthesis)
- Writer: $0.02-0.05 (generation)
- Journal: $0.00 (zero LLM)
- Task Manager: $0.00 (zero LLM)
- Rescue: $0.02-0.03 (diagnosis)

---

## Future Agent Ideas

Potential agents to add:

- **📊 Daily Briefing Agent**: Proactive morning briefings with overdue tasks, journal streaks, related knowledge suggestions
- **🎨 Designer Agent**: Generate diagrams and visuals
- **🔗 Connector Agent**: Integration with external services (Notion, Obsidian sync)
- **🤝 Collaborator Agent**: Multi-user coordination
- **🎓 Tutor Agent**: Interactive learning and teaching

---

**Last Updated**: 2026-02-08
**See Also**: ARCHITECTURE.md, README.md, RESCUE_SYSTEM.md
