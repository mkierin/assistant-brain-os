# 🚁 Self-Healing Rescue Agent System

**Goal**: Tasks should complete "no matter what" through intelligent AI-powered recovery.

Inspired by [Temporal](https://temporal.io/)'s durable execution model, but enhanced with AI diagnosis and auto-recovery.

---

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│  Normal Task Flow                                             │
└──────────────────────────────────────────────────────────────┘
User Request → Route to Agent → Worker Executes → Success ✅

┌──────────────────────────────────────────────────────────────┐
│  Failure with Rescue System                                   │
└──────────────────────────────────────────────────────────────┘
User Request → Route to Agent → Execution Fails
    ↓
Retry 1 → Fails
    ↓
Retry 2 → Fails
    ↓
Retry 3 → Fails
    ↓
🚁 RESCUE AGENT DISPATCHED
    ↓
AI Analyzes:
  - What was the goal?
  - What went wrong?
  - Why did it fail 3 times?
  - Can it be auto-fixed?
    ↓
Decision Tree:
  ├─ High Confidence Fix? → Auto-fix & Retry ✅
  ├─ Need Different Agent? → Re-route & Retry 🔄
  ├─ Code Bug? → Create PR Issue 📝
  └─ Complex/Unsafe? → Escalate to Human 🧑‍💻
```

---

## Architecture

### 1. Enhanced Failure Tracking

Every failure now captures:
- **Timestamp**: When it happened
- **Attempt number**: Which retry (1, 2, 3)
- **Agent**: Which agent failed
- **Error message**: What went wrong
- **Stack trace**: Full Python traceback
- **Input payload**: What was being processed

```python
class FailureDetail(BaseModel):
    timestamp: str
    attempt: int
    agent: str
    error_message: str
    stack_trace: Optional[str]
    input_payload: Dict[str, Any]
```

### 2. Rescue Context

When rescue agent is dispatched, it receives:
- **Complete workflow context**: What was the goal?
- **Full failure history**: All 3 attempts with errors
- **Original input**: What triggered the workflow
- **Agent code** (optional): Source code that failed
- **Worker logs** (optional): System logs

```python
class RescueContext(BaseModel):
    job_id: str
    workflow_goal: str
    failed_agent: str
    failure_count: int
    failure_history: List[FailureDetail]
    original_payload: Dict[str, Any]
    agent_code: Optional[str]
    worker_logs: Optional[str]
```

### 3. AI Diagnosis

The rescue agent uses LLM (DeepSeek/GPT-4) to:

1. **Analyze the failure pattern**
   - Same error 3 times? → Systematic issue
   - Different errors? → Unstable state
   - Transient error? → Retry might work

2. **Diagnose root cause**
   - Missing dependency?
   - Malformed input?
   - API rate limit?
   - Code bug?
   - External service down?

3. **Determine recovery strategy**
   - Can it be safely auto-fixed?
   - What's the confidence level?
   - What actions are needed?

```python
class RescueDiagnosis(BaseModel):
    root_cause: str
    can_auto_fix: bool
    recovery_strategy: RecoveryStrategy
    actions: List[Dict[str, Any]]
    confidence: float  # 0.0 to 1.0
    explanation: str
    pr_summary: Optional[str]
```

### 4. Recovery Strategies

#### Strategy A: **Retry with Modification** (80%+ confidence)
Modify job parameters and retry:
- Fix malformed URLs
- Adjust timeouts
- Change model/provider
- Use fallback values

**Example**: URL has typo → Fix it → Retry

#### Strategy B: **Route to Different Agent** (High confidence)
Original agent is wrong for this task:
- User asked for save, but agent tried to search
- Complex task, but simple agent assigned
- Agent lacks required capabilities

**Example**: content_saver failed on plain text → Route to simple_note_saver

#### Strategy C: **Apply Code Patch** (Use with extreme caution)
Auto-fix code issues:
- Install missing dependency: `pip install package`
- Fix obvious import error
- Add missing error handling
- **Only if safe and reversible**

**Example**: ImportError for youtube-transcript-api → Install it

#### Strategy D: **Skip Step** (If non-critical)
Continue workflow without this step:
- Optional enrichment failed
- Non-essential data missing
- Can proceed without it

**Example**: Thumbnail extraction failed → Continue without thumbnail

#### Strategy E: **Escalate to Human** (Default for low confidence)
Create detailed PR-ready issue:
- Complex bug requiring human judgment
- Safety concerns with auto-fix
- Multiple possible root causes
- Confidence < 80%

---

## PR-Ready Issue Reports

When escalating, rescue agent creates a comprehensive issue report:

### Example Issue

```markdown
# 🚨 content_saver fails: YouTube video has no captions available

**Issue ID**: RESCUE-20260205-113045
**Workflow**: Extract and save YouTube video
**Failed Agent**: content_saver
**Failure Rate**: 3/3 attempts

---

## Summary

YouTube video extraction fails when video has no captions. The
`youtube-transcript-api` raises `NoTranscriptFound` but the agent
doesn't handle this case gracefully.

## Root Cause Analysis

The agent assumes all YouTube videos have captions. When a video
doesn't have captions (auto-generated or manual), the API raises
`NoTranscriptFound` exception which is not caught.

Approximately 10% of YouTube videos don't have captions available.

## Reproduction Steps

1. User shares YouTube URL: https://youtube.com/watch?v=abc123
2. System detects URL and routes to content_saver
3. Agent calls extract_youtube_video() tool
4. Tool attempts: YouTubeTranscriptApi().fetch(video_id)
5. API raises: NoTranscriptFound
6. Exception bubbles up, agent crashes
7. Retries fail with same error (video still has no captions)

## Error Logs

**Latest Error**:
```
youtube_transcript_api._errors.NoTranscriptFound:
No transcripts were found for video ID: abc123
```

**Stack Trace**:
```python
File "agents/content_saver.py", line 245, in extract_youtube_video
    fetched = api.fetch(video_id, languages=['en'])
File "youtube_transcript_api/__init__.py", line 87, in fetch
    raise NoTranscriptFound(video_id)
youtube_transcript_api._errors.NoTranscriptFound:
No transcripts were found for video ID: abc123
```

## AI-Suggested Fix

**File**: `agents/content_saver.py`
**Function**: `extract_youtube_video()`
**Line**: 245

### Proposed Code Change:

```python
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

@content_saver_agent.tool
async def extract_youtube_video(ctx: RunContext[None], url: str) -> str:
    # ... existing code ...

    # Get transcript (with fallback for videos without captions)
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=['en'])
        transcript_text = " ".join([snippet.text for snippet in fetched.snippets])
    except NoTranscriptFound:
        # Graceful fallback: save metadata without transcript
        return f"""
⚠️ **Video has no captions available**

I can still save the video metadata, but won't be able to
extract the full transcript.

**Title**: {metadata['title']}
**Channel**: {metadata['channel']}
**URL**: {url}

Would you like me to:
1. Save metadata only (no transcript)
2. Skip this video
3. Wait for you to add a manual description

**Note**: You could also try Whisper transcription
(costs $0.006/minute) if you need the transcript.
"""

    # ... rest of existing code ...
```

### Alternative Solution:

Add Whisper fallback for videos without captions:
- Only activate if user explicitly requests it
- Cost: $0.006 per minute of audio
- More expensive but provides full transcript

## Impact Assessment

**Severity**: High (blocks core YouTube feature)
**Frequency**: ~10% of YouTube videos lack captions
**Users Affected**: All users sharing YouTube content
**Component**: content_saver agent

## Related Files

- `agents/content_saver.py` (primary fix needed)
- `agents/content_saver.py` line 245 (specific location)
- `common/config.py` (if adding Whisper fallback)

## Testing Checklist

- [ ] Test with video that has manual captions
- [ ] Test with video that has auto-generated captions
- [ ] Test with video that has NO captions (should gracefully handle)
- [ ] Test with non-English captions
- [ ] Test with private video
- [ ] Verify error message is user-friendly
- [ ] Ensure metadata is still saved when no transcript

---

**Created by**: Rescue Agent (AI-powered)
**Timestamp**: 2026-02-05T11:30:45
**Job ID**: a642e1b0
**Confidence**: 95%
```

---

## Key Features

### ✅ Like Temporal

- **Durable Execution**: Every task is tracked and recoverable
- **Automatic Retries**: Built-in retry logic (3 attempts)
- **Workflow Context**: Complete history of what happened
- **Observability**: Full logs and metrics for every job

### 🤖 Enhanced with AI

- **Intelligent Diagnosis**: LLM analyzes failures to find root cause
- **Auto-Recovery**: High-confidence fixes applied automatically
- **PR-Ready Issues**: Detailed reports for developers
- **Learning System**: Gets better over time with failure patterns

### 🛡️ Safety First

- **Conservative by Default**: Only auto-fix if confidence > 80%
- **No Destructive Actions**: Won't delete data or force operations
- **Reversible Changes**: Can roll back if needed
- **Human Escalation**: Complex issues always escalate

---

## Usage

### For Users

**Nothing changes!** The rescue system works automatically in the background.

If a task fails 3 times:
1. You'll see a "Rescue Agent" notification
2. System will either:
   - ✅ Auto-fix and complete the task
   - ⚠️ Notify you that it needs developer attention

### For Developers

**Check rescue issues**:
```bash
# View all rescue issues
ls -la /tmp/rescue_issues/

# Read latest issue
cat /tmp/rescue_issues/RESCUE-*.md | tail -1
```

**Monitor rescue activity**:
```bash
# Watch worker logs
pm2 logs brain-worker

# Look for rescue agent dispatches
grep "🚁 Rescue Agent" ~/.pm2/logs/brain-worker-out.log
```

---

## Configuration

### Confidence Threshold

Default: 80% - Only auto-fix if AI is 80%+ confident

To adjust, edit `agents/rescue_agent.py`:
```python
if diagnosis.can_auto_fix and diagnosis.confidence >= 0.8:
    # Auto-fix
```

### Retry Count

Default: 3 attempts before rescue

To adjust, edit `common/contracts.py`:
```python
class Job(BaseModel):
    max_retries: int = 3  # Change this
```

### LLM Model

Rescue agent uses the same model as configured in `.env`:
- `LLM_PROVIDER=deepseek` → Uses DeepSeek (cheaper)
- `LLM_PROVIDER=openai` → Uses GPT-4o (more powerful)

---

## Examples

### Example 1: Auto-Fixed URL Typo

**Failure**: User shared malformed YouTube URL
**Diagnosis**: URL has extra characters
**Recovery**: Fixed URL automatically
**Result**: Task completed successfully

```
🚁 Rescue Agent activated
🔍 Root Cause: URL malformed (extra params breaking video ID extraction)
💡 Strategy: retry_with_modification
🎯 Confidence: 95%
✅ Auto-fixing: Cleaned URL and retrying
✅ Task completed successfully!
```

### Example 2: Re-routed to Better Agent

**Failure**: content_saver failed on plain text note
**Diagnosis**: Wrong agent for task type
**Recovery**: Routed to simple_note_saver
**Result**: Note saved successfully

```
🚁 Rescue Agent activated
🔍 Root Cause: content_saver expects URLs, but received plain text
💡 Strategy: route_to_different_agent
🎯 Confidence: 90%
✅ Re-routing to: simple_note_saver
✅ Task completed successfully!
```

### Example 3: Created PR Issue

**Failure**: YouTube video has no captions
**Diagnosis**: Missing error handling for NoTranscriptFound
**Recovery**: Escalated with detailed PR
**Result**: Developer notified, issue documented

```
🚁 Rescue Agent activated
🔍 Root Cause: youtube-transcript-api raises NoTranscriptFound
💡 Strategy: escalate_to_human
🎯 Confidence: 65% (requires code changes)
📝 PR Issue Created: RESCUE-20260205-113045
⚠️ Task needs developer attention
```

---

## Benefits

### For Users
- **Higher Success Rate**: Most failures auto-recover
- **Better Error Messages**: Clear explanation when things fail
- **No Manual Retries**: System handles recovery automatically

### For Developers
- **Reduced On-Call**: Fewer "task failed" alerts
- **Better Bug Reports**: AI-generated issues with full context
- **Learning System**: Understand failure patterns
- **Self-Healing**: System fixes itself when possible

---

## Future Enhancements

Could add:
- **Pattern Learning**: Track common failures and optimize
- **Code Patching**: Actually apply code fixes automatically
- **Proactive Monitoring**: Predict failures before they happen
- **Custom Recovery Rules**: User-defined recovery strategies
- **Rescue Metrics**: Dashboard showing rescue success rate

---

## Technical Details

### Files Modified

- `common/contracts.py` - Added failure tracking contracts
- `agents/rescue_agent.py` - New AI-powered rescue agent
- `worker.py` - Enhanced failure handling and rescue dispatch

### Dependencies

- OpenAI SDK (for LLM diagnosis)
- Existing agent framework
- Redis (for job queue)

### Performance Impact

- **Normal operation**: Zero overhead (only activates on failure)
- **Rescue operation**: ~5-10 seconds for AI diagnosis
- **Cost**: $0.01-0.02 per rescue (DeepSeek API calls)

---

## Testing the Rescue System

Want to see it in action? Share a YouTube URL without captions:

```
https://youtube.com/watch?v=test123
```

The system will:
1. Try to extract transcript → Fail
2. Retry 3 times → All fail
3. Dispatch rescue agent → Analyzes failure
4. Either auto-fix or create PR issue

---

**Status**: ✅ Active and monitoring all task failures

**Rescue Success Rate**: TBD (just deployed)

**PR Issues Created**: Check `/tmp/rescue_issues/`
