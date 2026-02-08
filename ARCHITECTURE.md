# 🏗️ Assistant Brain OS - System Architecture

**Version**: 4.0 (Updated 2026-02-08)

Complete architecture documentation including Obsidian-style knowledge graph, advanced retrieval, YouTube extraction, self-healing rescue system, journal agent, and task manager.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Knowledge Graph Architecture](#knowledge-graph-architecture)
4. [Agent System](#agent-system)
5. [Self-Healing Rescue System](#self-healing-rescue-system)
6. [Data Flow](#data-flow)
7. [Storage Layer](#storage-layer)
8. [API Integrations](#api-integrations)
9. [Deployment](#deployment)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│  Telegram Bot  │  Voice Input  │  Web API (Future)              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                          │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   main.py    │    │  worker.py   │    │ Redis Queue  │    │
│  │   (Router)   │ →  │  (Executor)  │ ←  │  (Tasks)     │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│                                                                 │
│  - Message routing                                              │
│  - URL detection                                                │
│  - Casual vs actionable classification                          │
│  - Job queuing                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Agent System                             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  Content    │  │  Archivist  │  │  Researcher │           │
│  │  Saver      │  │  (Search)   │  │  (Deep)     │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Writer    │  │   Journal   │  │   Task Mgr  │           │
│  │  (Content)  │  │   (Diary)   │  │  (Reminders)│           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                                 │
│  ┌─────────────┐                                               │
│  │   Rescue    │                                               │
│  │   Agent     │                                               │
│  └─────────────┘                                               │
│                                                                 │
│  - Deterministic agents (zero LLM) + LLM-assisted agents       │
│  - Specialized capabilities                                     │
│  - Self-healing on failures                                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Knowledge Graph Layer                        │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Obsidian-Style Features                    │   │
│  │                                                          │   │
│  │  • Bidirectional Links: [[Note Title]]                 │   │
│  │  • Backlinks: Show all notes linking to this note      │   │
│  │  • Tag Hierarchy: #ai/ml/nlp → #ai/ml → #ai           │   │
│  │  • Daily Notes: YYYY-MM-DD temporal organization       │   │
│  │  • Network Graph: NetworkX for relationships           │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Implementation: common/knowledge_graph.py                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Retrieval System                             │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │           Advanced Retrieval Features                   │   │
│  │                                                          │   │
│  │  1. Hybrid Search (BM25 + Semantic)                    │   │
│  │     - Keyword matching (BM25Okapi)                     │   │
│  │     - Semantic similarity (embeddings)                  │   │
│  │     - Weighted combination (configurable)              │   │
│  │                                                          │   │
│  │  2. Contextual Retrieval (Anthropic)                   │   │
│  │     - Prepend context before embedding                 │   │
│  │     - "Document: X | Topics: Y | Z"                    │   │
│  │     - Better semantic understanding                     │   │
│  │                                                          │   │
│  │  3. Metadata Filtering                                  │   │
│  │     - Filter by tags, date, type                       │   │
│  │     - Combine with search                               │   │
│  │     - Precise results                                   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Implementation: common/database.py                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Storage Layer                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   ChromaDB   │  │   SQLite     │  │    Redis     │        │
│  │  (Vectors)   │  │  (Metadata)  │  │  (Queue/KV)  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│  ChromaDB: Vector embeddings, semantic search                  │
│  SQLite: Structured data, metadata, tasks, journal entries          │
│  Redis: Task queue, caching, job tracking                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Telegram Bot (`main.py`)

**Responsibilities**:
- Receive messages from Telegram
- Classify message type (casual, actionable, URL)
- Route to appropriate agent using **deterministic regex** (zero LLM)
- Handle voice transcription (Whisper)
- Provide user feedback
- Run reminder scheduler (every 15 min)

**Key Features**:
- URL detection with regex: `r'https?://[^\s]+'`
- `route_deterministic()` — pure regex routing, 11 steps
- Voice journal mode (auto-route voice → journal when enabled)
- Thinking messages for UX
- `/tasks` and `/journal` commands

**Flow**:
```python
1. Receive message
2. Check if voice + voice_journal setting
   → If voice_journal ON: Route to journal agent
3. Check if casual (is_casual_message)
   → If casual: Respond with AI chat
   → If actionable: Continue
4. Detect URLs
   → If URL: Route to content_saver
5. route_deterministic(text):
   → "save/remember" → archivist
   → "search/find" → archivist
   → "journal:/diary:" → journal
   → "remind me/todo" → task_manager
   → Questions → researcher
   → Default → researcher
6. Create Job and queue in Redis
7. Worker picks up and processes
8. Send result back to user
```

### 2. Worker System (`worker.py`)

**Responsibilities**:
- Process jobs from Redis queue
- Load and execute agents dynamically
- Handle retries and failures
- Track job status
- Send results to Telegram

**Enhanced Failure Handling**:
```python
try:
    # Execute agent
    response = await execute_agent(job)
except Exception as e:
    # Collect detailed failure info
    job.retry_count += 1
    failure_detail = {
        "timestamp": now,
        "attempt": job.retry_count,
        "error_message": str(e),
        "stack_trace": traceback.format_exc(),
        "input_payload": job.payload
    }
    job.history.append(failure_detail)

    if job.retry_count < 3:
        # Normal retry
        requeue(job)
    else:
        # 🚁 Dispatch rescue agent
        dispatch_rescue(job)
```

**Performance**:
- Multiple workers (2+ processes)
- BLPOP for efficient queue blocking
- 5-minute timeout on active jobs
- Long message chunking (4096 char limit)

### 3. Redis Queue Architecture

**Keys**:
- `brain:task_queue` - Main job queue (FIFO)
- `job:processing:{job_id}` - Active job tracking (5 min TTL)
- `job:completed:{job_id}` - Completed jobs (10 min TTL)
- User settings, cache, etc.

**Job Flow**:
```
Producer (main.py) → LPUSH → Queue → BLPOP → Worker
                                         ↓
                                    Execute Agent
                                         ↓
                                    Send Result
```

---

## Knowledge Graph Architecture

### Obsidian-Style Implementation

```
┌─────────────────────────────────────────────────────────────┐
│                    NetworkX Graph                           │
│                                                             │
│  Nodes: Knowledge entries (notes, articles, videos, etc.)  │
│  Edges: Relationships (mentions, mentioned-by, linked-to)  │
│                                                             │
│  Node Attributes:                                           │
│    - id: Unique identifier                                  │
│    - title: Note title                                      │
│    - type: note, article, youtube, daily-note, concept     │
│    - tags: List of hierarchical tags                        │
│    - created_at: Timestamp                                  │
│    - metadata: Custom fields                                │
│                                                             │
│  Edge Types:                                                │
│    - mentions: A → B (A mentions B via [[B]])              │
│    - mentioned-by: B → A (B is mentioned by A)             │
│    - tagged: Note → Tag                                     │
│    - parent-tag: #ai/ml → #ai                              │
│    - temporal: Note → Daily Note                            │
└─────────────────────────────────────────────────────────────┘
```

### Features Implementation

#### 1. Bidirectional Links

```python
def _parse_and_create_links(self, source_id, content, title):
    """Parse [[Note Title]] and create bidirectional edges"""
    pattern = r'\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, content + " " + title)

    for link_text in matches:
        target_id = self._find_note_by_title(link_text)
        if not target_id:
            # Create placeholder if note doesn't exist
            target_id = self._create_placeholder_note(link_text)

        # Bidirectional edges
        self.graph.add_edge(source_id, target_id, relationship='mentions')
        self.graph.add_edge(target_id, source_id, relationship='mentioned-by')
```

**Use Cases**:
- Connect related notes automatically
- Build conceptual networks
- Discover knowledge clusters

#### 2. Backlinks

```python
def get_backlinks(self, node_id: str) -> List[Dict]:
    """Get all notes that link TO this note"""
    backlinks = []
    for predecessor in self.graph.predecessors(node_id):
        if self.graph[predecessor][node_id]['relationship'] == 'mentioned-by':
            note_data = self.graph.nodes[predecessor]
            backlinks.append({
                "id": predecessor,
                "title": note_data['title'],
                "created_at": note_data['created_at']
            })
    return backlinks
```

**Use Cases**:
- See what references a concept
- Find related research
- Build literature maps

#### 3. Tag Hierarchy

```python
def _parse_tag_hierarchy(self, tag: str) -> List[str]:
    """Parse 'ai/ml/nlp' into ['ai', 'ai/ml', 'ai/ml/nlp']"""
    if '/' not in tag:
        return [tag]

    parts = tag.split('/')
    hierarchy = []
    for i in range(len(parts)):
        hierarchy.append('/'.join(parts[:i+1]))

    # Create parent-child edges
    for i in range(len(hierarchy) - 1):
        self.graph.add_edge(hierarchy[i+1], hierarchy[i],
                           relationship='parent-tag')

    return hierarchy
```

**Examples**:
- `#ai/ml/nlp` → `#ai/ml` → `#ai`
- `#programming/python/async` → hierarchy
- Search by parent tag finds all children

#### 4. Daily Notes

```python
def get_or_create_daily_note(self, date: str = None) -> str:
    """Get or create daily note (YYYY-MM-DD format)"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    daily_note_id = f"daily_{date}"

    if not self.graph.has_node(daily_note_id):
        # Create daily note with template
        self.graph.add_node(
            daily_note_id,
            title=f"Daily Note - {date}",
            type="daily-note",
            created_at=date,
            content="# {date}\n\n## Notes\n\n## Tasks\n\n## Links\n"
        )

    return daily_note_id
```

**Automatic Linking**:
- All notes created today link to today's daily note
- Create temporal organization
- Weekly/monthly views possible

---

## Agent System

### Agent Architecture

All agents use **PydanticAI** framework:

```python
from pydantic_ai import Agent, RunContext

agent = Agent(
    model,
    output_type=str,
    system_prompt="...",
    retries=3
)

@agent.tool
async def tool_function(ctx: RunContext[None], param: str) -> str:
    """Tool description for LLM"""
    # Tool implementation
    return result

async def execute(input: str) -> AgentResponse:
    """Entry point called by worker"""
    result = await agent.run(input)
    return AgentResponse(
        success=True,
        output=result.output
    )
```

### Agent Catalog

#### 1. Content Saver (`agents/content_saver.py`)

**Purpose**: Extract and save content from various sources

**Tools**:
- `extract_youtube_video()` - YouTube transcript + metadata
- `extract_tweet()` - Twitter/X posts
- `extract_webpage()` - Web articles
- `save_to_knowledge_graph()` - Store with bidirectional links
- `create_summary()` - LLM-generated summary
- `get_graph_stats()` - Knowledge graph metrics

**YouTube Processing Flow**:
```
1. Detect YouTube URL (youtube.com or youtu.be)
2. Extract video ID from URL
3. Get transcript using youtube-transcript-api (FREE)
4. Get metadata using yt-dlp (title, channel, duration, etc.)
5. Extract chapters from description
6. LLM summarization:
   - TL;DR (2-3 sentences)
   - Key Points (5-7 bullets)
   - Main Concepts
   - Notable Quotes
   - Suggested Tags
7. Create timestamp links (click to jump)
8. Save to knowledge graph with:
   - Full transcript (searchable)
   - Summary and metadata
   - Auto-generated tags
   - Links to daily note
   - Connections to related concepts
```

**Cost**: $0.01-0.02 per video (LLM only, transcript is free)

#### 2. Archivist (`agents/archivist.py`)

**Purpose**: Search and retrieve from knowledge base

**Tools**:
- `semantic_search()` - Vector similarity search
- `hybrid_search()` - BM25 + semantic (NEW)
- `search_with_filters()` - Metadata filtering (NEW)
- `get_backlinks()` - Obsidian-style backlinks (NEW)
- `get_by_tag_hierarchy()` - Tag-based retrieval (NEW)
- `get_daily_note()` - Retrieve daily notes (NEW)

**Search Strategies**:
```python
# Hybrid search (best of both worlds)
results = hybrid_search(
    query="machine learning transformers",
    keyword_weight=0.3,  # BM25 for exact matches
    semantic_weight=0.7   # Embeddings for concepts
)

# With metadata filters
results = search_with_filters(
    query="python tutorial",
    tags=["programming", "python"],
    date_from="2026-01-01",
    content_type="youtube"
)

# Contextual retrieval
# Embeddings include: "[Document: Title | Topics: tag1, tag2] content"
# Better semantic understanding
```

#### 3. Researcher (`agents/researcher.py`)

**Purpose**: Deep research with web search and synthesis

**Tools**:
- `web_search()` - DuckDuckGo search
- `fetch_webpage()` - Extract content
- `search_knowledge_base()` - Internal search
- `synthesize_findings()` - Combine sources

**Features**:
- Multi-source research
- Citation tracking
- Fact verification
- Report generation

#### 4. Writer (`agents/writer.py`)

**Purpose**: Content creation and editing

**Tools**:
- `create_draft()` - Generate content
- `edit_content()` - Refine and improve
- `format_markdown()` - Structure content
- `add_metadata()` - Tags and links

#### 5. Journal Agent (`agents/journal.py`)

**Purpose**: Voice & text journaling with auto-linking (zero LLM)

**Flow**:
```
1. Strip journal prefix ("journal:", "diary:", etc.)
2. Detect action (save vs view)
3. For save:
   a. Extract topics (keyword-based)
   b. Detect mood (regex patterns)
   c. Generate title (date + first sentence)
   d. Save to SQLite + ChromaDB with content_type="journal"
   e. Cross-link: search existing notes → create knowledge graph edges
4. For view:
   a. Query db.get_journal_entries(limit=7)
   b. Format as numbered list
```

#### 6. Task Manager (`agents/task_manager.py`)

**Purpose**: Deterministic task/reminder CRUD (zero LLM)

**Flow**:
```
1. Strip task prefix ("remind me to", "todo:", etc.)
2. Detect action (add/list/complete/delete)
3. For add:
   a. Extract date with dateparser ("tomorrow", "next Friday")
   b. Extract priority (urgent→high, no rush→low)
   c. Default reminder at 9 AM on due date
   d. Save to tasks table in SQLite
4. For complete:
   a. Match by #number or keyword overlap
   b. Mark as completed in DB
5. Scheduler: check_reminders() runs every 15 min
```

#### 7. Rescue Agent (`agents/rescue_agent.py`)

**Purpose**: Self-healing system for failed tasks

See [Self-Healing Rescue System](#self-healing-rescue-system) section below.

---

## Self-Healing Rescue System

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Failure Detection                        │
│                                                             │
│  Task fails → Retry 1 → Retry 2 → Retry 3                 │
│                                      ↓                      │
│                          Still failing? Dispatch Rescue     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Context Collection                        │
│                                                             │
│  • Job ID and workflow goal                                 │
│  • All 3 failure attempts with:                            │
│    - Timestamps                                             │
│    - Error messages                                         │
│    - Stack traces                                           │
│    - Input payloads                                         │
│  • Failed agent name                                        │
│  • Agent source code (optional)                             │
│  • Worker logs (optional)                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   AI Diagnosis (LLM)                        │
│                                                             │
│  Prompt includes:                                           │
│  • Full failure context                                     │
│  • Error patterns                                           │
│  • Available recovery strategies                            │
│  • Safety guidelines                                        │
│                                                             │
│  LLM analyzes and outputs:                                  │
│  • Root cause explanation                                   │
│  • Can it be auto-fixed? (confidence score)                │
│  • Recovery strategy to use                                 │
│  • Specific actions to take                                 │
│  • PR-ready issue (if escalating)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
           ┌─────────────┴─────────────┐
           │     Confidence >= 80%?     │
           └─────┬──────────────┬───────┘
             YES │              │ NO
                 ↓              ↓
    ┌─────────────────┐  ┌─────────────────┐
    │   Auto-Fix      │  │   Escalate      │
    │   & Retry       │  │   to Human      │
    └─────────────────┘  └─────────────────┘
           │                      │
           ↓                      ↓
    ✅ Task Succeeds      📝 Create PR Issue
```

### Recovery Strategies

#### Strategy 1: Retry with Modification
**When**: Parameters are incorrect but fixable
**Confidence**: 80%+
**Examples**:
- Malformed URL → Clean and normalize
- Timeout too short → Increase timeout
- Wrong format → Convert format

#### Strategy 2: Route to Different Agent
**When**: Wrong agent for the task
**Confidence**: 85%+
**Examples**:
- Plain text sent to content_saver → Route to note_saver
- Search query sent to writer → Route to archivist

#### Strategy 3: Apply Code Patch
**When**: Safe, reversible code fix
**Confidence**: 90%+
**Examples**:
- Missing package → `pip install package`
- Missing import → Add import statement
- ⚠️ Used with extreme caution

#### Strategy 4: Skip Step
**When**: Non-critical step fails
**Confidence**: 85%+
**Examples**:
- Thumbnail extraction failed → Continue without
- Optional enrichment failed → Use defaults

#### Strategy 5: Escalate to Human
**When**: Complex issue or low confidence
**Confidence**: < 80%
**Action**: Create comprehensive PR issue

### PR Issue Generation

When escalating, rescue agent creates:

```markdown
# 🚨 [Agent] fails: [Root Cause]

**Issue ID**: RESCUE-YYYYMMDD-HHMMSS
**Workflow**: [Original goal]
**Failed Agent**: [agent_name]
**Failure Rate**: 3/3 attempts

## Summary
[Clear explanation of what went wrong]

## Root Cause Analysis
[AI's detailed diagnosis of why it failed]

## Reproduction Steps
1. [Step by step to reproduce]
2. ...

## Error Logs
[Stack traces, error messages from all attempts]

## AI-Suggested Fix
[Specific code changes or configuration updates]

### Proposed Code:
```python
[Actual code fix with before/after]
```

## Impact Assessment
**Severity**: High/Medium/Low
**Frequency**: How often does this fail?
**Users Affected**: [Context]

## Testing Checklist
- [ ] Test with original failing input
- [ ] Test edge cases
- [ ] Verify no regression

---
**Created by**: Rescue Agent (AI)
**Confidence**: XX%
**Timestamp**: [ISO timestamp]
```

Saved to: `/tmp/rescue_issues/RESCUE-*.md`

### Integration with Worker

```python
# worker.py - Enhanced error handling

except Exception as e:
    # Collect detailed failure info
    failure_detail = FailureDetail(
        timestamp=datetime.now().isoformat(),
        attempt=job.retry_count,
        agent=job.current_agent,
        error_message=str(e),
        stack_trace=traceback.format_exc(),
        input_payload=job.payload
    )
    job.history.append(failure_detail)

    if job.retry_count < 3:
        # Normal retry
        requeue(job)
    else:
        # Dispatch rescue agent
        rescue_job = Job(
            current_agent="rescue_agent",
            payload={
                "failed_job": job.model_dump(),
                "context": {
                    "workflow_goal": job.payload.get("text"),
                    "failure_history": job.history,
                    "agent_code": None,
                    "worker_logs": None
                }
            }
        )
        queue.push(rescue_job)
```

---

## Data Flow

### 1. Content Ingestion Flow

```
User shares content
    ↓
Telegram Bot (main.py)
    ↓
URL Detection
    ↓
Route to content_saver
    ↓
Worker picks up job
    ↓
content_saver agent
    ├─ YouTube? → extract_youtube_video()
    │   ├─ Get transcript (youtube-transcript-api)
    │   ├─ Get metadata (yt-dlp)
    │   ├─ LLM summarization
    │   ├─ Detect chapters
    │   └─ Format with timestamps
    ├─ Tweet? → extract_tweet()
    ├─ Webpage? → extract_webpage()
    └─ Plain text? → save as note
    ↓
save_to_knowledge_graph()
    ├─ Parse [[links]]
    ├─ Parse #tags (with hierarchy)
    ├─ Create embeddings (contextual)
    ├─ Link to daily note
    ├─ Create bidirectional edges
    └─ Store in ChromaDB + SQLite
    ↓
Return formatted result
    ↓
Worker sends to Telegram
    ↓
User sees result
```

### 2. Search/Retrieval Flow

```
User asks question
    ↓
Telegram Bot
    ↓
Route to archivist
    ↓
Worker picks up job
    ↓
archivist agent decides:
    ├─ Simple query → semantic_search()
    ├─ Complex → hybrid_search()
    │   ├─ BM25 keyword scoring
    │   ├─ Semantic vector search
    │   └─ Weighted combination
    ├─ Need filtering → search_with_filters()
    │   ├─ Apply tag filter
    │   ├─ Apply date filter
    │   └─ Apply type filter
    └─ Backlinks → get_backlinks()
    ↓
Retrieve from ChromaDB + SQLite
    ↓
Format results with:
    ├─ Relevance scores
    ├─ Source metadata
    ├─ Links to related notes
    └─ Backlinks
    ↓
Return to user
```

### 3. Failure Recovery Flow

```
Task fails 3 times
    ↓
Worker dispatches rescue_agent
    ↓
rescue_agent collects context:
    ├─ All failure details
    ├─ Original goal
    ├─ Stack traces
    └─ Input payload
    ↓
AI diagnosis (LLM)
    ├─ Analyze failure pattern
    ├─ Determine root cause
    ├─ Assess fix confidence
    └─ Propose recovery
    ↓
Decision:
    ├─ High confidence? → Auto-fix & requeue
    └─ Low confidence? → Create PR issue
    ↓
Result sent to user
```

---

## Storage Layer

### ChromaDB (Vector Store)

```python
# Schema
Collection: "brain_knowledge"

Document structure:
{
    "id": "unique_id",
    "document": "[Context] Full content",  # Contextual retrieval
    "embedding": [0.1, 0.2, ...],          # 1536-dim vector
    "metadata": {
        "title": "Note title",
        "tags": ["tag1", "tag2"],
        "type": "youtube|article|note",
        "source": "telegram|web|...",
        "created_at": "ISO timestamp",
        "user_id": "telegram_id"
    }
}

# Contextual retrieval format:
"[Document: {title} | Topics: {tags}]\n\n{content}"
```

**Operations**:
- `add()` - Store new embeddings
- `query()` - Semantic search
- `get()` - Retrieve by ID
- `update()` - Modify metadata
- `delete()` - Remove entries

### SQLite (Metadata Store) — `data/brain.db`

**Tables**:

```sql
-- Knowledge Entries
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    tags TEXT DEFAULT '[]',        -- JSON array
    source TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',    -- JSON object
    created_at TEXT
);

-- Tasks & Reminders
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    due_date TEXT,
    reminder_at TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    tags TEXT DEFAULT '[]',
    linked_knowledge TEXT DEFAULT '[]',
    recurrence TEXT,
    created_at TEXT,
    completed_at TEXT
);
```

Journal entries are stored in the `knowledge` table with `metadata` containing `"content_type": "journal"`.

### NetworkX Graph (In-Memory)

```python
# Graph structure
G = nx.DiGraph()

# Nodes
G.add_node(
    "node_id",
    title="Title",
    type="note|article|youtube|daily-note|concept",
    tags=["tag1", "tag2"],
    created_at="ISO timestamp"
)

# Edges
G.add_edge(
    "source_id",
    "target_id",
    relationship="mentions|mentioned-by|parent-tag|temporal"
)

# Queries
backlinks = list(G.predecessors(node_id))
outgoing = list(G.successors(node_id))
neighbors = list(G.neighbors(node_id))
```

### Redis (Queue & Cache)

**Usage**:
- Task queue: `brain:task_queue`
- Job tracking: `job:processing:{id}`, `job:completed:{id}`
- User settings: `user:{user_id}:settings`
- Cache: Temporary data, embeddings cache
- Rate limiting: Request throttling

---

## API Integrations

### LLM Providers

**Primary**: DeepSeek
- Model: `deepseek-chat`
- Use: Agents, summaries, diagnosis
- Cost: ~$0.01 per 1000 tokens

**Secondary**: OpenAI
- Model: `gpt-4o` (agents), `whisper-1` (transcription)
- Use: Complex reasoning, voice transcription
- Cost: Variable

**Configuration** (`.env`):
```bash
LLM_PROVIDER=deepseek  # or openai
MODEL_NAME=deepseek-chat
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
```

### Embedding Provider

**OpenAI Embeddings**:
- Model: `text-embedding-3-small`
- Dimensions: 1536
- Cost: $0.02 per 1M tokens

### External Services

**YouTube**:
- `youtube-transcript-api` - Free transcript extraction
- `yt-dlp` - Free metadata extraction
- No API key needed

**Twitter/X**:
- Web scraping or API (future)

**Web Scraping**:
- `playwright` for JavaScript-heavy sites
- `beautifulsoup4` for static HTML

---

## Deployment

### Process Management (PM2)

```bash
# Services
pm2 start main.py --name brain-bot       # Telegram bot
pm2 start worker.py --name brain-worker -i 2  # 2 workers

# Monitoring
pm2 list           # Show all processes
pm2 logs           # View logs
pm2 restart all    # Restart services
```

### File Structure

```
assistant-brain-os/
├── main.py                 # Telegram bot & deterministic router
├── worker.py               # Job executor
├── manage.py               # CLI management
│
├── agents/
│   ├── content_saver.py    # YouTube, web, tweet extraction
│   ├── archivist.py        # Search & retrieval (deterministic)
│   ├── researcher.py       # Deep research (LLM for synthesis)
│   ├── writer.py           # Content creation
│   ├── journal.py          # Voice/text journaling (zero LLM)
│   ├── task_manager.py     # Task/reminder CRUD (zero LLM)
│   ├── coder.py            # Code generation
│   └── rescue_agent.py     # Self-healing system
│
├── common/
│   ├── database.py         # SQLite + ChromaDB + hybrid search
│   ├── knowledge_graph.py  # NetworkX graph + Obsidian features
│   ├── config.py           # Configuration
│   └── contracts.py        # Data models (Job, AgentResponse, etc.)
│
├── tests/
│   ├── test_bug_fixes.py       # Core agent tests
│   ├── test_message_handling.py # Routing tests
│   ├── test_task_manager.py    # 61 task manager tests
│   ├── test_journal.py         # 51 journal tests
│   ├── test_skill_loader.py    # Skill system tests
│   ├── test_coder.py           # Coder agent tests
│   └── test_goal_tracker.py    # Goal tracker tests
│
└── data/
    ├── brain.db            # SQLite database
    └── chroma/             # ChromaDB vector store
```

### Environment Variables

```bash
# Required
TELEGRAM_TOKEN=...
DEEPSEEK_API_KEY=...
OPENAI_API_KEY=...

# Optional
LLM_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
REDIS_URL=redis://localhost:6379
DATABASE_PATH=data/brain.db
CHROMA_PATH=data/chroma
```

---

## Performance Metrics

### Latency

- URL detection: < 1ms (regex)
- Agent routing: < 1ms (deterministic regex, zero LLM)
- Journal save: < 50ms (deterministic)
- Task CRUD: < 20ms (deterministic)
- YouTube extraction: 5-10s (transcript + metadata + LLM)
- Semantic search: ~100-300ms (vector similarity)
- Hybrid search: ~200-400ms (BM25 + semantic)
- Rescue diagnosis: ~3-5s (LLM analysis)

### Cost per Operation

- YouTube save: $0.01-0.02 (LLM summary only)
- Web article save: $0.005-0.01 (extraction + summary)
- Search query: $0.001-0.002 (embedding + retrieval)
- Rescue attempt: $0.02-0.03 (detailed LLM diagnosis)
- Voice transcription: $0.006/minute (Whisper)

### Scale

- **Current**: Single user, ~1000 entries
- **Target**: Multi-user, 100K+ entries per user
- **Bottlenecks**: ChromaDB queries, NetworkX graph size
- **Optimization**: Sharding, caching, lazy loading

---

## Future Enhancements

### Planned Features

1. **Multi-user Support**
   - User isolation
   - Shared knowledge spaces
   - Permissions

2. **Advanced Graph Features**
   - Graph visualization UI
   - Path finding between concepts
   - Community detection
   - Centrality metrics

3. **Content Generation**
   - Automated note taking
   - Meeting summaries
   - Research reports
   - Blog post generation

4. **Integrations**
   - Notion sync
   - Obsidian import/export
   - GitHub sync
   - Email integration

5. **Rescue System Enhancements**
   - Pattern learning from past failures
   - Proactive failure prediction
   - Automatic code patching
   - A/B testing recovery strategies

---

## Version History

- **v4.0** (2026-02-08): Journal agent, task manager, deterministic routing, 362 tests
- **v3.0** (2026-02-05): Rescue system, YouTube, Obsidian features
- **v2.0** (2026-02-04): Knowledge graph, agents
- **v1.0** (2026-02-03): Initial release

---

**Last Updated**: 2026-02-08
**Maintained By**: Development Team
**Questions**: See README.md or AGENTS.md
