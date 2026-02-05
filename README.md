# Assistant Brain OS 🧠

A modular multi-agent system designed to act as your "Second Brain." It listens for input via Telegram (voice and text), intelligently routes requests to specialized AI agents, and processes tasks asynchronously while building a searchable knowledge base with Obsidian-style features.

## ✨ Latest Features (v3.0)

### 🎥 YouTube Video Intelligence
- **Automatic transcript extraction** (free, no API key needed)
- **Smart summarization** with AI (TL;DR, key points, concepts, quotes)
- **Chapter detection** with clickable timestamps
- **Full-text search** of video content
- Works with 90%+ of videos that have captions
- Cost: $0.01-0.02 per video (LLM summary only)

### 📚 Obsidian-Style Knowledge Graph
- **Bidirectional links**: `[[Note Title]]` creates two-way connections
- **Backlinks view**: See all notes that reference a concept
- **Tag hierarchy**: `#ai/ml/nlp` creates parent-child relationships
- **Daily notes**: Temporal organization (YYYY-MM-DD)
- **NetworkX graph**: Visualize knowledge connections
- **Auto-linking**: Notes automatically connect to daily notes and related concepts

### 🔍 Advanced Retrieval System
- **Hybrid search**: BM25 keyword + semantic vector search
- **Contextual retrieval**: Anthropic's approach for better understanding
- **Metadata filtering**: Search by tags, date, content type
- **Ranked results**: Weighted combination of search methods
- **Backlink traversal**: Follow knowledge connections

### 🚁 Self-Healing Rescue System
- **AI-powered failure recovery**: Tasks auto-fix when they fail
- **Intelligent diagnosis**: LLM analyzes root causes
- **Auto-recovery**: High-confidence fixes applied automatically
- **PR-ready issues**: Detailed bug reports for developers
- **Inspired by Temporal**: Durable execution with AI enhancement
- **5 recovery strategies**: Retry, re-route, patch, skip, or escalate

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [User Experience Features](#user-experience-features)
- [Testing](#testing)
- [Security](#security)
- [Setup & Installation](#setup--installation)
- [How It Works](#how-it-works)
- [Agent System](#agent-system)
- [Troubleshooting](#troubleshooting)
- [Possible Improvements](#possible-improvements)
- [Documentation](#documentation)

---

## 🏗️ Architecture

### High-Level System Architecture

```mermaid
graph TB
    subgraph "User Interface"
        TG[Telegram Bot]
        TGU[Telegram User]
    end

    subgraph "Orchestration Layer"
        MAIN[main.py<br/>Orchestrator/Producer]
        ROUTER[Intent Router<br/>LLM-based]
    end

    subgraph "Queue System"
        REDIS[(Redis Queue)]
    end

    subgraph "Worker Layer"
        W1[Worker 1<br/>worker.py]
        W2[Worker 2<br/>worker.py]
    end

    subgraph "Agent System"
        ARCH[Archivist Agent<br/>Save/Search Knowledge]
        RES[Researcher Agent<br/>Web Research]
        WRI[Writer Agent<br/>Format Content]
    end

    subgraph "Storage Layer"
        SQLITE[(SQLite<br/>Metadata)]
        CHROMA[(ChromaDB<br/>Vector Store)]
    end

    subgraph "External Services"
        DEEPSEEK[DeepSeek API<br/>LLM & Analysis]
        OPENAI[OpenAI API<br/>Whisper STT]
        TAVILY[Tavily API<br/>AI Research]
        DDG[DuckDuckGo<br/>Free Search]
        BRAVE[Brave Search<br/>Optional]
        PLAYWRIGHT[Playwright<br/>Web Scraping]
    end

    TGU -->|Text/Voice| TG
    TG -->|Receive Message| MAIN
    MAIN -->|STT| OPENAI
    MAIN -->|Route Intent| ROUTER
    ROUTER -->|Enqueue Job| REDIS
    ROUTER -->|Track Status| REDIS

    REDIS -->|Pop Job| W1
    REDIS -->|Pop Job| W2

    W1 -->|Load & Execute| ARCH
    W1 -->|Load & Execute| RES
    W1 -->|Load & Execute| WRI
    W2 -->|Load & Execute| ARCH
    W2 -->|Load & Execute| RES
    W2 -->|Load & Execute| WRI

    ARCH -->|Query/Store| SQLITE
    ARCH -->|Vector Search| CHROMA
    RES -->|Multi-Source Search| TAVILY
    RES -->|Multi-Source Search| DDG
    RES -->|Multi-Source Search| BRAVE
    RES -->|Cache Results| CHROMA
    RES -->|Browse Pages| PLAYWRIGHT
    WRI -->|Query Context| CHROMA

    ARCH -->|LLM Calls| DEEPSEEK
    RES -->|Query Analysis| DEEPSEEK
    RES -->|Synthesis| DEEPSEEK
    WRI -->|Content Generation| DEEPSEEK

    W1 -->|Natural Response| TG
    W2 -->|Natural Response| TG
    W1 -->|Log Activity| REDIS
    W2 -->|Log Activity| REDIS
    TG -->|Send Response| TGU

    style MAIN fill:#4CAF50
    style W1 fill:#2196F3
    style W2 fill:#2196F3
    style ARCH fill:#FF9800
    style RES fill:#FF9800
    style WRI fill:#FF9800
    style REDIS fill:#F44336
    style SQLITE fill:#9C27B0
    style CHROMA fill:#9C27B0
```

### Process Management Architecture

```mermaid
graph LR
    subgraph "PM2 Process Manager"
        P1[brain-bot<br/>main.py<br/>PID: 1]
        P2[brain-worker<br/>worker.py<br/>Instance 1<br/>PID: 2]
        P3[brain-worker<br/>worker.py<br/>Instance 2<br/>PID: 3]
    end

    subgraph "Services"
        R[Redis<br/>Port 6379]
        DB[ChromaDB<br/>File-based]
    end

    P1 -->|Push Jobs| R
    P2 -->|Pop Jobs| R
    P3 -->|Pop Jobs| R

    P2 -->|Read/Write| DB
    P3 -->|Read/Write| DB

    style P1 fill:#4CAF50
    style P2 fill:#2196F3
    style P3 fill:#2196F3
    style R fill:#F44336
    style DB fill:#9C27B0
```

---

## 🔧 Technology Stack

### Core Framework
- **Python 3.12+** - Primary language
- **PydanticAI** - Agent framework with tool support
- **python-telegram-bot** - Telegram integration
- **AsyncIO** - Asynchronous execution

### AI & LLM Services
- **DeepSeek API** - Primary LLM provider (cost-effective)
  - Agent reasoning & synthesis
  - Query analysis & breakdown
  - Natural conversation
- **OpenAI API** - Voice transcription only
  - Whisper STT for voice messages

### Research APIs (Multi-Source)
- **Tavily** - AI-optimized research (primary)
  - $0.002 per search
  - 1000 free searches/month
  - AI-generated summaries + sources
- **DuckDuckGo** - Free web search (secondary)
  - Unlimited searches
  - Privacy-focused
  - Good general coverage
- **Brave Search** - Optional third source
  - 2000 free searches/month
  - Comprehensive results

### Data Storage
- **ChromaDB** - Vector database
  - Semantic search
  - Search result caching (24hr)
  - Knowledge embeddings
- **SQLite** - Metadata storage
  - Structured data
  - Knowledge entries
- **Redis** - Multi-purpose
  - Job queue (FIFO)
  - Active job tracking
  - Completion logging
  - User settings

### Infrastructure
- **PM2** - Process management
  - 1 bot instance
  - 2 worker instances (parallel processing)
  - Auto-restart, monitoring
- **Playwright** - Web scraping
  - Full page content extraction
  - JavaScript rendering

### Development & Testing
- **pytest** - Testing framework
  - 45+ test cases
  - Async support
  - Real API testing
- **pytest-cov** - Coverage reporting

### Monitoring & Logging
- **PM2 logs** - Process output
- **Redis tracking** - Job status
- **Custom `/monitor` command** - Real-time activity

---

## 🔧 System Components

### 1. **Main Bot (main.py)** - The Orchestrator/Producer

**Responsibilities:**
- Listens to Telegram messages (text & voice)
- Converts voice messages to text using OpenAI Whisper
- Routes user requests to appropriate agents using LLM-based intent classification
- Enqueues jobs into Redis with unique job IDs
- Sends immediate acknowledgment to users

**Key Features:**
- Multi-modal input (text + voice)
- Intelligent intent routing
- Asynchronous job queuing

### 2. **Worker Processes (worker.py)** - The Consumers

**Responsibilities:**
- Continuously poll Redis queue for new jobs
- Dynamically load agent classes based on job type
- Execute agent tasks with error handling
- Implement retry logic (max 3 attempts)
- Send results/errors back to users via Telegram

**Key Features:**
- Multiple worker instances for parallel processing
- Dynamic agent loading using `importlib`
- Fault tolerance with retries
- Job failure notifications

### 3. **Agent System** - Specialized AI Workers

#### **Archivist Agent** (`agents/archivist.py`)
- **Purpose:** Knowledge management and retrieval
- **Tools:**
  - `save_knowledge()`: Store information with tags and embeddings
  - `search_knowledge()`: Semantic search through stored knowledge
- **Use Cases:** Saving notes, retrieving past information, building knowledge base

#### **Researcher Agent** (`agents/researcher.py`)
- **Purpose:** Multi-source deep research and information gathering
- **Strategy:** Query analysis → Multi-source search → Cross-verification → Synthesis
- **Tools:**
  - `analyze_query()`: Break complex queries into focused sub-questions
  - `search_brain()`: Check existing knowledge cache first
  - `search_tavily()`: AI-optimized research with summaries (primary source)
  - `search_web_ddg()`: DuckDuckGo free search (secondary source)
  - `search_brave()`: Brave Search for additional coverage (optional)
  - `browse_page()`: Extract full content from URLs using Playwright
- **Features:**
  - Smart caching (24hr) to reduce API costs
  - Parallel multi-source searching
  - Cross-source verification
  - Natural language synthesis
- **Use Cases:** Research topics, complex analysis, fact-checking, latest information
- **Performance:**
  - Simple queries: 20-30s (1-2 sources)
  - Complex queries: 60-90s (all sources + analysis)

#### **Writer Agent** (`agents/writer.py`)
- **Purpose:** Content formatting and synthesis
- **Tools:**
  - `get_context()`: Retrieve relevant knowledge for writing
- **Use Cases:** Draft emails, format reports, synthesize information

### 4. **Storage Layer**

#### **SQLite Database** (`data/brain.db`)
- Stores metadata about knowledge entries
- Manages structured data
- Fast relational queries

#### **ChromaDB** (`data/chroma/`)
- Vector database for semantic search
- Stores embeddings of knowledge entries
- **Search result caching** (24-hour TTL)
  - Tavily results cached per query
  - DuckDuckGo results cached per query
  - Brave results cached per query
- Enables RAG (Retrieval-Augmented Generation)
- Reduces API costs by reusing recent searches

### 5. **Redis** (Port 6379)
- **Job queue** with FIFO processing
  - Asynchronous task distribution
  - Enables horizontal scaling of workers
- **Real-time monitoring**
  - Active job tracking (`job:processing:*`)
  - Completion logging (`job:completed:*`)
  - Duration metrics
- **User settings storage**
  - Preferences per user
  - Configuration persistence
- **Agent activity logs**
  - Tool execution tracking
  - Performance metrics

---

## 🔄 Data Flow

### Message Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant T as Telegram Bot
    participant M as main.py
    participant R as Redis Queue
    participant W as Worker
    participant A as Agent
    participant DB as Storage
    participant LLM as DeepSeek

    U->>T: Send message (text/voice)
    T->>M: Forward message

    alt Voice Message
        M->>LLM: Transcribe with Whisper
        LLM-->>M: Return text
    end

    M->>LLM: Route intent (Archivist/Researcher/Writer)
    LLM-->>M: Return agent + payload

    M->>R: Enqueue Job (ID, agent, payload)
    M->>T: Send acknowledgment with Job ID
    T->>U: "Job queued: ABC123"

    R->>W: Worker pops job
    W->>W: Load agent class dynamically
    W->>A: Execute with payload

    loop Agent Processing
        A->>DB: Query/Store data
        A->>LLM: Make LLM calls
        LLM-->>A: Return response
    end

    A-->>W: Return result

    alt Success
        W->>T: Send success message
        T->>U: Display result
    else Error
        W->>W: Retry (max 3x)
        alt All Retries Failed
            W->>T: Send error notification
            T->>U: "Task failed after 3 retries"
        end
    end
```

### Knowledge Storage Flow

```mermaid
graph TD
    A[User Input] -->|Save Request| B[Archivist Agent]
    B -->|Extract Text & Tags| C{Process Knowledge}
    C -->|Generate Embedding| D[ChromaDB]
    C -->|Store Metadata| E[SQLite]
    D -->|Vector| F[Knowledge Base]
    E -->|Structured Data| F

    G[Search Query] -->|Semantic Search| D
    D -->|Top K Results| H[Retrieve Context]
    E -->|Metadata| H
    H -->|Augmented Context| I[LLM Response]

    style B fill:#FF9800
    style D fill:#9C27B0
    style E fill:#9C27B0
    style F fill:#4CAF50
```

---

## 🎨 User Experience Features

### Intelligent Message Handling

The bot provides a sophisticated user experience with context-aware responses and natural conversation flow.

#### 1. **Smart Message Detection**

The system automatically distinguishes between casual conversation and actionable requests:

```python
# Casual messages (get AI-generated responses)
- Greetings: "hi", "hello", "hey"
- Thanks: "thanks", "thank you"
- Goodbyes: "bye", "goodbye"
- Acknowledgments: "ok", "got it", "sure"
- Short responses: Very brief messages

# Actionable messages (routed to agents)
- Save requests: "Remember that...", "Save this..."
- Search queries: "What did I say about...", "Find..."
- Research requests: "Research...", "Look up..."
- Writing tasks: "Write a...", "Draft..."
```

#### 2. **Dynamic "Thinking" Messages**

When processing requests, users receive one of 34 randomized status messages to provide feedback without repetition:

```
🧠 Processing your request...
🤔 Analyzing your message...
💭 Thinking about this...
🔍 Looking into that...
⚙️ Working on it...
... and 29 more variations
```

#### 3. **AI-Powered Casual Responses**

Casual conversations are handled by DeepSeek with high creativity (temperature=0.8), ensuring natural, non-repetitive responses:

```python
User: "Hi!"
Bot: "Hey there! How can I help you today?"  # AI-generated, always unique

User: "Thanks!"
Bot: "You're welcome! Let me know if you need anything else."  # Different each time
```

#### 4. **Clear Agent Status Messages**

When tasks are queued, users get crystal-clear feedback about what's happening:

```
📚 Archivist Agent
Saving your knowledge to the brain...

🔬 Researcher Agent
Researching and gathering information...

✍️ Writer Agent
Drafting and formatting content...
```

#### 5. **Interactive Telegram Commands**

The bot includes a comprehensive command menu accessible via Telegram's menu button:

```
/start  - 🏠 Welcome & overview
/help   - 📖 Detailed help & examples
/status - 📊 Check system status
/search - 🔍 Search your knowledge base
/stats  - 📈 View usage statistics
/settings - ⚙️ Configure preferences
```

#### 6. **User Settings Interface**

Interactive settings with inline keyboard buttons for easy configuration:

```python
# Adjustable settings
- Thinking message style (random/fixed/emoji-only)
- Response verbosity (brief/normal/detailed)
- Notification preferences
- Default agent selection
```

#### 7. **Real-Time Voice Feedback**

When processing voice messages:
1. "🎤 Transcribing your voice message..."
2. Shows transcription result
3. Confirms processing with agent status

---

## 🧪 Testing

### Comprehensive Test Suite

The system includes **45+ test cases** across **6 test files**, providing robust coverage of all critical functionality.

#### Test Files

1. **`tests/test_contracts.py`** ✅ (15 tests - All passing)
   - Job model creation and validation
   - KnowledgeEntry model testing
   - AgentResponse structure validation
   - Status enumerations
   - Serialization/deserialization

2. **`tests/test_agents.py`** (12+ tests)
   - Archivist save/search operations
   - Researcher web research capabilities
   - Writer content formatting
   - Error handling for all agents
   - Empty/invalid input handling

3. **`tests/test_message_handling.py`** (15+ tests)
   - Casual message detection
   - Actionable message detection
   - Intent routing logic
   - User settings management
   - Thinking message variations

4. **`tests/test_worker.py`** (8+ tests)
   - Successful job processing
   - Retry logic on failures
   - Max retries enforcement
   - Agent chaining
   - Dynamic agent loading

5. **`tests/test_integration.py`** (8+ tests)
   - End-to-end save→search workflow
   - Research→write workflow
   - Error recovery
   - Concurrent operations
   - Data persistence

6. **`tests/test_config.py`** (3+ tests)
   - Environment variable loading
   - Default values
   - Required configuration

#### Running Tests

```bash
# Quick run (using test runner)
./run_tests.sh

# Manual run
source venv/bin/activate
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# Run specific test file
python -m pytest tests/test_contracts.py -v

# Run by marker
pytest tests/ -m unit           # Only unit tests
pytest tests/ -m integration    # Only integration tests
```

#### Test Coverage

```
Data models:      100% covered ✅
Agent interfaces: 100% covered ✅
Agent logic:      ~80% covered (mocked LLM calls)
Message handling: ~80% covered
Worker logic:     ~80% covered
Overall:          >80% coverage target
```

**See:** `TESTING_GUIDE.md` for detailed testing documentation.

---

## 🔒 Security

### Comprehensive Protection

The repository is secured against accidental exposure of sensitive information with **80+ .gitignore patterns**.

#### Protected Information

```
✅ Environment files (.env, .env.*)
✅ API keys and credentials
✅ Database files (*.db, *.sqlite)
✅ Vector databases (ChromaDB, Qdrant)
✅ User data directories (data/, backups/)
✅ Log files (*.log, .pm2/)
✅ Temporary files (temp/, *.tmp)
✅ Voice recordings (*.ogg, *.mp3)
✅ Redis dumps (dump.rdb)
✅ Python artifacts (__pycache__/, venv/)
✅ IDE files (.vscode/, .idea/)
✅ Personal notes (notes.md, todo.md)
```

#### Security Files

1. **`.gitignore`** - Comprehensive protection rules
2. **`.env.example`** - Safe configuration template (no secrets)
3. **`SECURITY_CHECKLIST.md`** - Security audit procedures
4. **`SECURITY_SUMMARY.md`** - Implementation verification

#### Verification

```bash
# Verify .env is ignored
git check-ignore -v .env
# Should output: .gitignore:9:*.env	.env

# Check no secrets in staging
git diff --cached | grep -iE "(api_key|secret|password|token)"
# Should return nothing

# List tracked files
git ls-files | grep ".env"
# Should return nothing
```

#### Best Practices

**DO:**
- ✅ Store secrets in `.env` file (never committed)
- ✅ Use `.env.example` as template
- ✅ Rotate API keys quarterly
- ✅ Review `git status` before every commit
- ✅ Add specific files only (`git add filename.py`)

**DON'T:**
- ❌ Use `git add .` (might add everything)
- ❌ Hardcode secrets in code
- ❌ Commit `.env` file
- ❌ Share keys via chat/email
- ❌ Use production keys in development

**See:** `SECURITY_CHECKLIST.md` for incident response procedures and key rotation schedules.

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.12+
- Node.js 20+ (for PM2)
- Redis server
- Telegram bot token
- OpenAI API key (for Whisper)
- DeepSeek API key (for LLM)

### Installation Steps

1. **Clone and Navigate**
   ```bash
   cd /root/assistant-brain-os
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Install Redis**
   ```bash
   sudo apt-get update
   sudo apt-get install -y redis-server
   sudo systemctl enable redis-server
   sudo systemctl start redis-server
   ```

5. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and tokens
   ```

   Required environment variables:
   ```env
   OPENAI_API_KEY=your_openai_key
   DEEPSEEK_API_KEY=your_deepseek_key
   TELEGRAM_TOKEN=your_telegram_bot_token
   LLM_PROVIDER=deepseek
   REDIS_URL=redis://localhost:6379
   DATABASE_PATH=data/brain.db
   CHROMA_PATH=data/chroma
   ```

6. **Initialize Data Directory**
   ```bash
   mkdir -p data logs
   ```

7. **Deploy with PM2**
   ```bash
   pm2 start ecosystem.config.js
   pm2 save
   ```

8. **Verify Deployment**
   ```bash
   pm2 list
   pm2 logs
   ```

---

## 💡 How It Works

### 1. User Sends Message

User sends text or voice message to Telegram bot:
- **Text:** "Save this: Machine learning is a subset of AI"
- **Voice:** Records audio explanation

### 2. Message Reception & Transcription

`main.py` receives the message:
```python
# Voice messages are transcribed
if update.message.voice:
    transcript = whisper_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    text = transcript.text
```

### 3. Intent Routing

LLM analyzes the message and determines which agent should handle it:
```python
routing = await route_intent(text)
# Returns: {"agent": "archivist", "payload": {"text": "...", "action": "save"}}
```

Routing logic considers:
- Keywords (save, search, research, write)
- Context of the request
- User's intent

### 4. Job Queuing

Job is created and pushed to Redis:
```python
job = Job(
    id=uuid.uuid4(),
    current_agent="archivist",
    payload={"text": "...", "source": "telegram", "user_id": 123}
)
r.lpush(TASK_QUEUE, job.model_dump_json())
```

### 5. Worker Processing

Worker continuously polls Redis:
```python
while True:
    job_data = r.brpop(TASK_QUEUE, timeout=5)
    if job_data:
        job = Job.model_validate_json(job_data[1])
        agent = load_agent(job.current_agent)  # Dynamic import
        result = await agent.execute(job.payload)
```

### 6. Agent Execution

Agent uses PydanticAI framework with tools:
```python
@archivist_agent.tool
async def save_knowledge(ctx, text: str, tags: List[str], source: str):
    # Generate embedding and store
    entry = KnowledgeEntry(text=text, tags=tags, source=source)
    db.add_knowledge(entry)
    return "Knowledge saved"
```

### 7. Result Delivery

Worker sends result back to user via Telegram:
```python
await context.bot.send_message(
    chat_id=user_id,
    text=f"✅ Task completed: {result}"
)
```

---

## 🤖 Agent System

### Available Agents

#### 1. 💾 Content Saver Agent
**Purpose**: Extract and save content from various sources

**Capabilities**:
- **YouTube videos**: Transcript extraction (free!), metadata, LLM summary
  - Works with 90%+ of videos with captions
  - Extracts: TL;DR, key points, concepts, quotes, chapters
  - Cost: $0.01-0.02 per video
- **Web articles**: Full content extraction with Playwright
- **Twitter/X**: Tweet extraction and threading
- **Plain notes**: Save text with auto-tagging

**Tools**:
- `extract_youtube_video()` - YouTube intelligence
- `extract_tweet()` - Twitter/X posts
- `extract_webpage()` - Web scraping
- `save_to_knowledge_graph()` - Obsidian-style storage with [[links]] and #tags
- `create_summary()` - AI summarization
- `get_graph_stats()` - Knowledge graph metrics

**Example**: Share `https://youtube.com/watch?v=abc123` → Extracts transcript, summarizes, saves with tags

#### 2. 📚 Archivist Agent
**Purpose**: Search and retrieve from knowledge base

**Capabilities**:
- **Hybrid search**: BM25 keyword + semantic vector (configurable weights)
- **Contextual retrieval**: Enhanced embeddings with document context
- **Metadata filtering**: Filter by tags, date, content type
- **Backlinks**: Obsidian-style "what links here"
- **Tag hierarchy**: Search parent tag finds all children
- **Daily notes**: Temporal retrieval

**Tools**:
- `semantic_search()` - Vector similarity
- `hybrid_search()` - Combined keyword + semantic (NEW)
- `search_with_filters()` - Advanced filtering (NEW)
- `get_backlinks()` - Show all notes linking to concept (NEW)
- `get_by_tag_hierarchy()` - Hierarchical tag search (NEW)
- `get_daily_note()` - Retrieve daily notes (NEW)

**Example**: "Find videos about machine learning" → Hybrid search with type=youtube filter

#### 3. 🔬 Researcher Agent
**Purpose**: Deep web research with multi-source aggregation

**Capabilities**:
- Multi-source search (Tavily, DuckDuckGo, Brave)
- Web page extraction and analysis
- Citation tracking
- Source synthesis
- Knowledge base integration

**Tools**:
- `web_search()` - Multi-provider search
- `fetch_webpage()` - Content extraction
- `search_knowledge_base()` - Internal search
- `synthesize_findings()` - Combine sources

**Example**: "Research transformer architecture papers" → Searches web + KB, synthesizes findings

#### 4. ✍️ Writer Agent
**Purpose**: Content creation and formatting

**Capabilities**:
- Draft generation
- Content editing and refinement
- Markdown formatting
- Auto-tagging and linking

**Tools**:
- `create_draft()` - Generate content
- `edit_content()` - Refine and improve
- `format_markdown()` - Structure content
- `add_metadata()` - Tags and [[links]]

**Example**: "Write a blog post about X using my notes" → Retrieves context, generates draft

#### 5. 🚁 Rescue Agent (NEW)
**Purpose**: Self-healing system for failed tasks

**Capabilities**:
- **AI diagnosis**: LLM analyzes failures to find root cause
- **Auto-recovery**: Attempts intelligent fixes
- **5 strategies**: Retry with modification, re-route, code patch, skip, escalate
- **PR generation**: Creates detailed bug reports
- **Learning system**: Improves over time

**How It Works**:
1. Task fails 3 times → Rescue agent dispatched
2. AI analyzes: error patterns, stack traces, context
3. High confidence (>80%)? → Auto-fix and retry
4. Low confidence? → Create PR-ready issue for developers

**Example**: YouTube extraction fails → Diagnoses "NoTranscriptFound", creates PR with suggested fix

### Agent Architecture

Each agent follows this pattern (updated for DeepSeek compatibility):
```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from contracts import AgentResponse

# Initialize with DeepSeek provider
# IMPORTANT: Use output_type=str for DeepSeek compatibility
# DeepSeek doesn't support structured outputs (Pydantic models)
agent = Agent(
    model=OpenAIModel('deepseek-chat', provider='deepseek'),
    output_type=str,  # Changed from AgentResponse
    system_prompt="Agent instructions..."
)

# Define tools
@agent.tool
async def tool_function(ctx: RunContext, param: str) -> str:
    # Tool implementation
    return result

# Execution wrapper
class AgentClass:
    async def execute(self, payload: dict) -> AgentResponse:
        try:
            result = await agent.run(prompt)

            # Manually wrap string output in AgentResponse
            return AgentResponse(
                success=True,
                output=result.output,  # Changed from result.data
                next_agent=None,
                data=None,
                error=None
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                output="",
                next_agent=None,
                data=None,
                error=str(e)
            )
```

### Key Implementation Notes

**DeepSeek Compatibility:**
- Use `output_type=str` instead of `output_type=AgentResponse`
- DeepSeek doesn't support structured outputs (Pydantic models as output)
- Manually wrap the string response in `AgentResponse` objects
- Access result with `result.output` (not `result.data`)

**Provider Configuration:**
```python
# Correct way to initialize DeepSeek
model = OpenAIModel('deepseek-chat', provider='deepseek')

# The provider='deepseek' string tells PydanticAI to:
# - Use DEEPSEEK_API_KEY from environment
# - Point to https://api.deepseek.com
# - Handle DeepSeek-specific API quirks
```

### Agent Communication

Agents can communicate via the knowledge base:
1. **Archivist** stores information
2. **Researcher** queries stored knowledge before web search
3. **Writer** retrieves context from knowledge base

This creates a **shared memory system** across agents.

---

## 🐛 Troubleshooting

### Common Issues

#### 1. **Worker Errors: "AsyncOpenAI object has no attribute client"**
**Cause:** Incorrect DeepSeek provider initialization
**Fix:** Ensure agents use `provider='deepseek'` string:
```python
model = OpenAIModel('deepseek-chat', provider='deepseek')
```

#### 2. **Agent Errors: "Unknown keyword arguments: result_type"**
**Cause:** Using older PydanticAI API
**Fix:** Use `output_type` instead of `result_type`:
```python
agent = Agent(model, output_type=AgentResponse)
```

#### 3. **Redis Connection Errors**
**Cause:** Redis not running
**Fix:**
```bash
sudo systemctl start redis-server
redis-cli ping  # Should return PONG
```

#### 4. **Import Errors: "name 'List' is not defined"**
**Cause:** Missing typing imports
**Fix:** Add to agent files:
```python
from typing import List
import uuid
```

#### 5. **ChromaDB Errors**
**Cause:** Database not initialized
**Fix:**
```bash
mkdir -p data/chroma
python check_system.py  # Verify setup
```

#### 6. **Telegram Bot Not Responding**
**Cause:** Wrong token or bot not running
**Fix:**
```bash
pm2 restart brain-bot
pm2 logs brain-bot  # Check for errors
```

### Debugging Commands

```bash
# Check all processes
pm2 list

# View logs
pm2 logs brain-bot --lines 50
pm2 logs brain-worker --lines 50

# Check Redis queue
redis-cli LLEN task_queue

# Clear failed jobs
redis-cli DEL task_queue

# Restart everything
pm2 restart all

# Check system status
python check_system.py
```

### Log Locations

- **PM2 Logs:** `/root/.pm2/logs/`
- **Application Logs:** `/root/assistant-brain-os/logs/`
- **Redis Logs:** `/var/log/redis/redis-server.log`

---

## 🚀 Possible Improvements

### High Priority

#### 1. **Health Monitoring**
```python
# Add health check endpoint
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "redis": check_redis_connection(),
        "database": check_db_connection(),
        "workers": get_worker_count(),
        "queue_size": get_queue_size()
    }
```

#### 2. **Job Status Tracking**
```python
# Store job status in Redis
JOB_STATUS_KEY = "job_status:{job_id}"

# Allow users to check job status
await context.bot.send_message(
    text=f"Job {job_id} status: {status}"
)
```

#### 3. **Dead Letter Queue**
```python
# Move failed jobs to separate queue for analysis
DEAD_LETTER_QUEUE = "dead_letter_queue"

if retry_count >= MAX_RETRIES:
    r.lpush(DEAD_LETTER_QUEUE, job.model_dump_json())
```

#### 4. **Rate Limiting**
```python
from redis import Redis
from datetime import datetime, timedelta

def rate_limit(user_id: int, limit: int = 10, window: int = 60):
    """Limit requests per user"""
    key = f"rate_limit:{user_id}"
    current = r.incr(key)
    if current == 1:
        r.expire(key, window)
    return current <= limit
```

#### 5. **Metrics & Analytics**
```python
# Track usage metrics
from prometheus_client import Counter, Histogram

job_counter = Counter('jobs_total', 'Total jobs processed')
job_duration = Histogram('job_duration_seconds', 'Job processing time')
agent_counter = Counter('agent_calls_total', 'Agent calls', ['agent_name'])
```

### Medium Priority

#### 6. **User Context Management**
```python
# Store user conversation context
class UserContext:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history = []
        self.preferences = {}

    def add_message(self, message: str):
        self.history.append(message)
        # Keep last 10 messages
        self.history = self.history[-10:]
```

#### 7. **Multi-Language Support**
```python
# Add language detection and translation
from langdetect import detect

detected_lang = detect(text)
if detected_lang != 'en':
    text = translate(text, source=detected_lang, target='en')
```

#### 8. **Agent Chaining**
```python
# Allow agents to call other agents
class Job:
    next_agent: str | None = None
    chain_data: dict = {}

# Researcher can call Writer to format results
if needs_formatting:
    job.next_agent = "writer"
    job.chain_data = {"research_results": results}
```

#### 9. **Webhook Integration**
```python
# Allow external systems to send data
@app.post("/webhook/{agent_name}")
async def webhook_handler(agent_name: str, data: dict):
    job = Job(current_agent=agent_name, payload=data)
    r.lpush(TASK_QUEUE, job.model_dump_json())
    return {"job_id": job.id}
```

#### 10. **Backup & Recovery**
```bash
# Automated backups
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf backup_${DATE}.tar.gz data/
rsync -av backup_${DATE}.tar.gz remote_server:/backups/
```

### Low Priority

#### 11. **Web Dashboard**
```python
# Add admin dashboard
from fastapi.templating import Jinja2Templates

@app.get("/dashboard")
async def dashboard():
    return templates.TemplateResponse("dashboard.html", {
        "workers": get_worker_stats(),
        "jobs": get_recent_jobs(),
        "agents": get_agent_stats()
    })
```

#### 12. **Agent Marketplace**
```python
# Allow users to enable/disable agents
class AgentRegistry:
    def __init__(self):
        self.available_agents = {
            "archivist": {"enabled": True, "description": "..."},
            "researcher": {"enabled": True, "description": "..."},
            "writer": {"enabled": True, "description": "..."}
        }
```

#### 13. **Advanced RAG Features**
```python
# Implement hybrid search (vector + keyword)
def hybrid_search(query: str, k: int = 5):
    vector_results = chroma.query(query, n_results=k)
    keyword_results = sqlite_fts_search(query, limit=k)
    return merge_and_rerank(vector_results, keyword_results)
```

#### 14. **Cost Tracking**
```python
# Monitor API costs
class CostTracker:
    def track_llm_call(self, tokens: int, model: str):
        cost = calculate_cost(tokens, model)
        r.hincrby("costs", f"{model}:{date}", cost)
```

---

## 📊 Monitoring Checklist

### Daily Checks
- [ ] Verify all PM2 processes are online
- [ ] Check Redis queue size (should be near 0)
- [ ] Review error logs for recurring issues
- [ ] Monitor API usage and costs

### Weekly Checks
- [ ] Backup database and vector store
- [ ] Review dead letter queue for patterns
- [ ] Update dependencies if needed
- [ ] Check disk space usage

### Monthly Checks
- [ ] Analyze agent performance metrics
- [ ] Review and optimize slow queries
- [ ] Clean up old logs
- [ ] Update documentation

---

## 📚 External API Resources

### Framework & Library Documentation

- **PydanticAI Documentation:** https://ai.pydantic.dev/
  - Agent system, tools, and structured outputs
- **python-telegram-bot Docs:** https://docs.python-telegram-bot.org/
  - Telegram bot API wrapper
- **ChromaDB Documentation:** https://docs.trychroma.com/
  - Vector database and embedding operations
- **Redis Documentation:** https://redis.io/docs/
  - Queue management and caching
- **DeepSeek API:** https://platform.deepseek.com/docs
  - LLM provider API reference
- **OpenAI Whisper:** https://platform.openai.com/docs/guides/speech-to-text
  - Voice transcription API

---

## 📝 License

This project is part of a personal assistant system. Ensure API keys are kept secure.

---

## 🎯 Quick Commands Reference

```bash
# Start everything
pm2 start ecosystem.config.js

# Stop everything
pm2 stop all

# Restart with new code
pm2 restart all

# View logs
pm2 logs

# Check Redis
redis-cli ping
redis-cli LLEN task_queue

# Check processes
pm2 list
pm2 monit

# Clear queue
redis-cli DEL task_queue

# Backup data
tar -czf backup.tar.gz data/

# Test bot locally
python main.py
```

---

## 📚 Documentation

### Complete Documentation Set

This repository includes 10 focused documentation files covering all aspects of the system:

#### **📖 Core Documentation**
1. **`README.md`** (this file)
   - Complete system architecture
   - Technology stack
   - Setup & installation
   - Agent system overview
   - Troubleshooting guide

2. **`AGENTS.md`**
   - Original agent specifications
   - Agent design patterns
   - Tool development guide

#### **👤 User Guides**
3. **`TELEGRAM_GUIDE.md`**
   - How to use the bot
   - Command reference
   - Example interactions
   - Voice message guide
   - Tips and tricks

#### **🔬 Research System**
4. **`MULTI_SOURCE_RESEARCH.md`**
   - Multi-source research architecture
   - Tavily + DuckDuckGo + Brave integration
   - Query analysis & breakdown
   - Caching strategy
   - Performance optimization

#### **🔍 Monitoring & Operations**
5. **`MONITORING_GUIDE.md`**
   - Real-time monitoring with `/monitor`
   - Parallel processing (2 workers)
   - PM2 logs and metrics
   - Redis tracking
   - Performance benchmarks

6. **`SETUP_COMPLETE.md`**
   - Deployment summary
   - Running services
   - PM2 process management
   - Quick troubleshooting

#### **🧪 Testing**
7. **`TESTING_GUIDE.md`**
   - General test suite overview
   - Running all tests
   - Test coverage

8. **`RESEARCHER_TESTING.md`**
   - Researcher-specific tests (30+ tests)
   - Real API testing (not mocked)
   - Edge cases
   - Performance tests

9. **`TEST_RESULTS.md`**
   - Latest test findings
   - Performance analysis
   - Optimization opportunities

#### **🔒 Security**
10. **`SECURITY_CHECKLIST.md`**
    - Pre-commit checklist
    - Incident response
    - Key rotation schedules
    - Security best practices

---

### Quick Reference

| Need to... | Read this file |
|------------|----------------|
| **Understand the system** | `README.md` (start here) |
| **Use the bot** | `TELEGRAM_GUIDE.md` |
| **Monitor activity** | `MONITORING_GUIDE.md` |
| **Research capabilities** | `MULTI_SOURCE_RESEARCH.md` |
| **Run tests** | `TESTING_GUIDE.md` or `RESEARCHER_TESTING.md` |
| **Add new agents** | `AGENTS.md` |
| **Security audit** | `SECURITY_CHECKLIST.md` |
| **Deploy/troubleshoot** | `SETUP_COMPLETE.md` |
| **Test results** | `TEST_RESULTS.md` |

---

## 🤝 Contributing

When adding new features:
1. Create new agent in `/agents/` following existing pattern
2. Add agent to intent router in `main.py`
3. Update `AGENTS.md` with agent documentation
4. Add tests in `/tests/` (maintain >80% coverage)
5. Update this README with architectural changes
6. Test with both text and voice inputs
7. Verify security (run `.env` not committed)

### Code Style
- Use async/await throughout
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Document complex logic with comments
- Use descriptive variable names

### Testing Requirements
- All new agents must have tests in `tests/test_agents.py`
- Maintain minimum 80% code coverage
- All tests must pass before merging
- Add integration tests for multi-agent workflows

---

**Built with ❤️ using PydanticAI and DeepSeek**
