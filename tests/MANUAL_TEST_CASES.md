# Manual Test Cases - Second Brain Assistant Bug Fixes

## How to Run Automated Tests

```bash
cd /root/assistant-brain-os
source venv/bin/activate
python -m pytest tests/test_bug_fixes.py -v
```

---

## Manual Test Cases by Bug Category

### 1. Rescue Agent No Longer Crashes on Import

**What was broken:** `rescue_agent.py` imported `MODEL_NAME` from `config.py` but it didn't exist, causing an ImportError at startup.

**Test:**
```bash
cd /root/assistant-brain-os
source venv/bin/activate
python -c "from common.config import MODEL_NAME; print(f'MODEL_NAME = {MODEL_NAME}')"
```

**Expected:** Prints `MODEL_NAME = deepseek-chat` or `MODEL_NAME = gpt-4o-mini` (no error).

---

### 2. Casual Message Detection No Longer Has False Positives

**What was broken:** Messages like "ok cool find me info about AI" were treated as casual greetings because they started with "ok".

**Test via Telegram:**
- Send: `ok cool now research quantum computing` -> Should route to researcher (NOT respond with casual chat)
- Send: `thanks, now save this note: Python is great` -> Should route to archivist (NOT casual)
- Send: `nice, what did I save about AI?` -> Should search knowledge (NOT casual)
- Send: `hello, can you help me write an email?` -> Should route to writer (NOT casual)
- Send: `hi` -> Should respond with casual chat (this IS casual)
- Send: `thanks` -> Should respond with casual chat (this IS casual)
- Send: `ok` -> Should respond with casual chat (this IS casual)

---

### 3. Database Entries Can Be Deleted

**What was broken:** `delete_entry()` used `WHERE embedding_id = ?` but the column is `id`, so deletes silently did nothing.

**Test via Telegram:**
1. Send: `Save this: test delete entry`
2. Wait for confirmation
3. Send: `delete that` or `remove last one`
4. Should see "Removed: ..." confirmation
5. Send: `search for test delete entry`
6. Should NOT find the deleted entry

---

### 4. Web Interface Chat Works End-to-End

**What was broken:**
- Web messages always routed to "archivist" regardless of content
- Worker never sent responses back to web users (only tried Telegram)

**Test:**
1. Open the web interface and login
2. Go to Chat
3. Send: `research machine learning basics`
4. Should get a research response (not an archivist save/search response)
5. Send: `write an email thanking my team`
6. Should get a formatted email draft
7. Send: `https://example.com`
8. Should trigger content saving

---

### 5. Web Dashboard Shows Correct Stats

**What was broken:** Knowledge stats endpoint misinterpreted ChromaDB result format, returning wrong numbers.

**Test:**
1. Open web interface -> Dashboard
2. Stats should show real numbers (Total Entries, This Week, Last Updated)
3. Numbers should match what you see in Knowledge Base
4. Go to Knowledge Base -> Search should return actual entries

---

### 6. Web Knowledge Base Search Works

**What was broken:** `/knowledge/entries` endpoint returned wrong format.

**Test:**
1. Open web interface -> Knowledge Base
2. Should see a list of saved entries (if any exist)
3. Type a search query and click Search
4. Results should appear with titles, summaries, dates
5. Click an entry -> modal should show full content

---

### 7. YouTube Video Processing Respects LLM Provider

**What was broken:** YouTube summary always used DeepSeek API even when LLM_PROVIDER was set to "openai".

**Test (if using OpenAI):**
1. Set `LLM_PROVIDER=openai` in `.env`
2. Restart the bot
3. Send a YouTube URL via Telegram
4. Should successfully process using OpenAI (not fail with DeepSeek auth error)

---

### 8. System Status Shows Correct Emoji

**What was broken:** `/status` command showed red emoji for Redis even when connected.

**Test via Telegram:**
1. Send: `/status`
2. Should show green emoji next to "Redis: Connected"
3. Should NOT show red emoji when Redis is actually connected

---

### 9. Knowledge Graph Backlinks Work

**What was broken:** `get_backlinks()` crashed on MultiDiGraph because it expected flat edge data but got nested dict-of-dicts.

**Test:**
1. Save content with [[links]]: `Save this: [[Machine Learning]] is a subset of [[AI]]`
2. Save another note: `Save this: [[AI]] powers modern [[Machine Learning]] applications`
3. The system should create bidirectional links without crashing
4. Backlinks should be queryable

---

### 10. Monitor Page Works

**What was broken:** Monitor stats endpoint misinterpreted knowledge data format.

**Test:**
1. Open web interface -> Monitor
2. Should show System Statistics (queue length, conversations, entries, etc.)
3. Should show Knowledge Topics
4. Should show Task Queue
5. Activity Log should display recent events
6. No errors in browser console

---

## Quick Smoke Test Script

Run this to verify key imports and basic functionality:

```bash
cd /root/assistant-brain-os
source venv/bin/activate

echo "=== Testing imports ==="
python -c "
from common.config import MODEL_NAME, LLM_PROVIDER, TASK_QUEUE
print(f'Config OK: {LLM_PROVIDER}, {MODEL_NAME}')

from common.contracts import Job, AgentResponse, RescueContext
print('Contracts OK')

from common.database import db
print(f'Database OK: {db.get_all_entries_count()} entries')

from common.knowledge_graph import KnowledgeGraph
print('Knowledge Graph OK')

from main import is_casual_message
assert is_casual_message('hi') == True
assert is_casual_message('ok cool research AI') == False
assert is_casual_message('https://example.com') == False
print('Casual detection OK')

print()
print('All basic checks passed!')
"
```
