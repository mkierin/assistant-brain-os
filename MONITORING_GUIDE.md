# 🔍 Monitoring & Parallel Processing Guide

## ✅ Fixed Issues

**Error Fixed**: `database.search_knowledge() got unexpected keyword argument n_results`
- Changed all `n_results=` to `limit=` in researcher.py
- All search functions now work correctly

## 🎯 Parallel Processing - How It Works

### Architecture

```
User 1: "Research quantum computing"  ─┐
                                       ├──→ Redis Queue (FIFO)
User 2: "Search for Python notes"   ──┘            ↓
                                          ┌─────────┴─────────┐
                                          │                   │
                                    Worker 1            Worker 2
                                    (Task 1)            (Task 2)
                                       ↓                   ↓
                                   Researcher          Archivist
                                       ↓                   ↓
                                   Result 1            Result 2
```

### You Have 2 Workers Running in Parallel

```bash
pm2 list
# brain-worker (id: 2) - Worker Instance 1
# brain-worker (id: 3) - Worker Instance 2
```

**This means:**
- ✅ **2 tasks can process simultaneously**
- ✅ If Worker 1 is busy, Worker 2 picks up the next job
- ✅ Both workers share the same Redis queue (FIFO)
- ✅ Complex research on one worker doesn't block simple queries on the other

### Example Timeline

```
00:00 - User A: "Research AI" (queued)
00:01 - Worker 1 picks up "Research AI" (30s task)
00:05 - User B: "Save this note" (queued)
00:06 - Worker 2 picks up "Save this note" (5s task)
00:11 - Worker 2 completes, idle
00:15 - User C: "Search for meetings" (queued)
00:16 - Worker 2 picks up "Search for meetings" (8s task)
00:24 - Worker 2 completes
00:31 - Worker 1 completes "Research AI"

Result: All 3 tasks done in 31 seconds (vs 43 seconds sequential)
```

## 📊 Monitoring Commands

### 1. `/monitor` - Real-Time Activity

Shows:
- **Queue Status**: How many jobs pending
- **Currently Processing**: Which agents are running (on both workers)
- **Recent Completions**: Last 5 jobs with durations
- **Recent Agent Activity**: What tools agents called

**Example Output:**
```
🔍 Real-Time Monitoring

📊 Queue Status:
• Pending jobs: 2
• Worker instances: 2 (parallel processing)
• Max concurrent: 2 tasks at once

⚡ Currently Processing:
• 🔄 Researcher Agent (started 5s ago)
• 🔄 Archivist Agent (started 2s ago)

✅ Recent Completions:
• ✓ Researcher Agent (23s)
• ✓ Writer Agent (8s)
• ✓ Archivist Agent (3s)
```

### 2. `/queue` - Pending Jobs

Shows:
- Total jobs waiting
- Expected processing time
- Worker status

### 3. `/status` - System Health

Shows:
- Worker processes online/offline
- Redis connection
- Queue size
- System configuration

### 4. PM2 Logs - Detailed Worker Activity

```bash
# Watch all workers in real-time
pm2 logs brain-worker

# Last 50 lines
pm2 logs brain-worker --lines 50

# Only errors
pm2 logs brain-worker --err

# Specific worker instance
pm2 logs brain-worker --id 2
```

## 🔍 What You'll See in Logs

### When Job Starts
```
🔄 Processing Job: d71fd7a3 | Agent: researcher | User: 123456789
```

### During Research (Multi-Source)
The agent will call tools - you'll see in logs:
```
Searching brain for: quantum computing
Tavily search: quantum computing developments 2026
DuckDuckGo search: quantum computing latest news
```

### When Job Completes
```
✅ Job d71fd7a3 completed | Agent: researcher | Duration: 23s
```

### When Job Fails
```
❌ Error processing job d71fd7a3: database error
♻️  Retrying job d71fd7a3 (attempt 2/3)
```

### After Max Retries
```
🚨 Job d71fd7a3 failed permanently after 3 retries
```

## 📈 Monitoring Metrics

### Queue Metrics (via Redis)

```bash
# Check queue size
redis-cli LLEN task_queue

# View active jobs
redis-cli KEYS "job:processing:*"

# View completed jobs (last 10 min)
redis-cli KEYS "job:completed:*"

# Get job details
redis-cli GET "job:processing:abc123"
```

### Worker Metrics (via PM2)

```bash
# Process status
pm2 list

# Resource usage (CPU, Memory)
pm2 monit

# Restart count (high = problems)
pm2 list | grep restarts
```

## 🎯 Understanding Job Flow

### Single User - Sequential

```
User sends 3 messages quickly:
1. "Research AI" → Queue position 1
2. "Save note" → Queue position 2
3. "Search docs" → Queue position 3

Worker 1: Picks #1, processes 30s
Worker 2: Picks #2, processes 5s, DONE, picks #3, processes 8s

Total time: ~30s (parallel processing saves time!)
```

### Multiple Users - Parallel

```
User A: "Research quantum" → Worker 1 (30s)
User B: "Save meeting notes" → Worker 2 (5s)
User C: "Search Python" → Waits for free worker
User D: "Write email" → Waits for free worker

After 5s: Worker 2 free, picks User C task
After 8s: Worker 2 free, picks User D task
After 30s: Worker 1 free

All 4 users served efficiently!
```

## 🚨 Troubleshooting

### Issue: Queue Growing (Jobs piling up)

**Check:**
```bash
redis-cli LLEN task_queue
# If > 10, something's wrong
```

**Possible causes:**
- Workers crashed: `pm2 list` (should show 2 workers online)
- Jobs taking too long: Check what's processing with `/monitor`
- Too many requests: Rate limiting needed

**Fix:**
```bash
# Restart workers
pm2 restart brain-worker

# Clear stuck queue (careful!)
redis-cli DEL task_queue
```

### Issue: Jobs Failing Repeatedly

**Check logs:**
```bash
pm2 logs brain-worker --err --lines 100
```

**Common causes:**
- API errors (Tavily, DeepSeek down)
- Database errors (ChromaDB issues)
- Code bugs (check error message)

**Fix:**
- Check API keys valid
- Check disk space: `df -h`
- Review code changes

### Issue: One Worker Down

**Check:**
```bash
pm2 list
# Both workers should show "online"
```

**Fix:**
```bash
pm2 restart brain-worker
```

### Issue: No Activity Visible in /monitor

**Cause:** Jobs processing too fast, Redis keys expire

**Solution:** This is normal! It means:
- No jobs currently processing (workers idle)
- Recent jobs completed quickly

## 📊 Performance Benchmarks

### Typical Job Durations

| Task Type | Single Source | Multi-Source (3 APIs) | Tools Called |
|-----------|---------------|----------------------|--------------|
| Save note | 2-3s | N/A | save_knowledge |
| Search knowledge | 3-5s | N/A | search_knowledge |
| Simple research | 8-12s | 15-25s | search_tavily, search_ddg |
| Complex research | 15-25s | 30-45s | analyze_query, search_tavily, search_ddg, search_brave |
| Deep research | 30-45s | 60-90s | All tools + browse_page |

### Parallel vs Sequential

**2 Users, 2 Research Tasks (30s each):**
- **Sequential**: 60 seconds total
- **Parallel (2 workers)**: 30 seconds total
- **Speedup**: 2x faster

**5 Users, Mixed Tasks:**
- **Sequential**: 5s + 30s + 8s + 3s + 15s = 61s
- **Parallel (2 workers)**: ~38s (overlapping execution)
- **Speedup**: 1.6x faster

## 🎛️ Scaling Up (Future)

### Add More Workers

Current: 2 workers
```javascript
// ecosystem.config.js
{name: 'brain-worker', instances: 2}
```

Scale to 4 workers:
```javascript
{name: 'brain-worker', instances: 4}
```

**When to scale:**
- Queue consistently > 5 jobs
- Response time > 60s regularly
- Many concurrent users

**Trade-offs:**
- More memory usage (75MB per worker)
- More CPU usage
- Faster processing

## 🔔 Monitoring Best Practices

### Daily
- Check `/status` - System healthy?
- Check `/monitor` - Any stuck jobs?
- Review `pm2 logs --lines 50` - Unusual errors?

### Weekly
- Check `pm2 list` - Restart counts increasing?
- Review failed jobs - Patterns?
- Check disk space - ChromaDB growing?

### Monthly
- Analyze job durations - Getting slower?
- Review API usage - Hitting limits?
- Check for optimization opportunities

## 📱 User Experience

### What Users See

**Instant acknowledgment:**
```
User: "Research quantum computing"
Bot: "Interesting topic! Let me research that for you."
[Job queued and processing in background]
```

**Natural result:**
```
[30 seconds later]
Bot: [3-5 paragraphs of comprehensive research with sources]
```

**If multiple requests:**
```
User: "Research AI" (Worker 1 processes)
User: "Save note" (Worker 2 processes immediately)
Both complete, no blocking!
```

### What You See (Monitoring)

**Via `/monitor`:**
```
Currently Processing:
• 🔄 Researcher Agent (started 5s ago)

Recent Completions:
• ✓ Archivist Agent (3s)
```

**Via `pm2 logs`:**
```
🔄 Processing Job: abc123 | Agent: researcher | User: 123
Tavily search: quantum computing
DuckDuckGo search: quantum computing 2026
✅ Job abc123 completed | Duration: 23s
```

## 🎯 Summary

**You now have:**
- ✅ **2 workers** processing jobs in parallel
- ✅ **`/monitor`** command for real-time activity
- ✅ **Enhanced logging** showing what agents are doing
- ✅ **Job tracking** in Redis with durations
- ✅ **Clear visibility** into system performance

**To monitor:**
1. **Real-time**: `/monitor` command in Telegram
2. **Detailed**: `pm2 logs brain-worker`
3. **Metrics**: `pm2 monit` for resource usage
4. **Queue**: `/queue` or `redis-cli LLEN task_queue`

**Next time you send a research query, watch:**
- The logs: `pm2 logs brain-worker --lines 0`
- Send query via Telegram
- See the job processing live!
- Use `/monitor` to see status
