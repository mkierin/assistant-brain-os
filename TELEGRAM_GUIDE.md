# 📱 Telegram Bot User Guide

## 🚀 Quick Start

### First Time Setup
1. Open Telegram and find your bot
2. Send `/start` to initialize
3. Configure your preferences with `/settings`
4. Start sending messages!

---

## 🎯 Available Commands

### Essential Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and overview |
| `/help` | Detailed help with examples |
| `/settings` | Configure bot preferences |
| `/status` | Check system status |
| `/agents` | Learn about each agent |
| `/queue` | View pending jobs |

### What Each Command Does

#### `/start` - Welcome Screen
Shows you what the bot can do and gives you a quick overview of features.

#### `/help` - Complete Guide
Detailed examples for each agent type:
- How to save knowledge
- How to search your brain
- How to research topics
- How to format content

#### `/settings` - Your Control Panel
Interactive menu to configure:
- **Auto-Route:** Let AI choose the right agent (recommended)
- **Voice Messages:** Enable/disable voice transcription
- **Notifications:** Get updates when jobs complete
- **Default Agent:** Choose which agent to use by default
- **Max Retries:** How many times to retry failed jobs

#### `/status` - System Health
Shows:
- Redis connection status
- Queue size
- Your current settings
- LLM provider info

#### `/agents` - Agent Documentation
Detailed info about:
- What each agent does
- Available tools
- Example requests
- When to use each one

#### `/queue` - Job Queue
See how many jobs are pending and estimated processing times.

---

## 🤖 Using the Agents

### 📚 Archivist - Your Knowledge Manager

**Best for:**
- Saving notes and thoughts
- Building a knowledge base
- Searching past information

**Example Messages:**

```
Save this: Machine learning uses neural networks

Remember: Team meeting every Monday at 10am

Save: Python is great for data science

What did I save about machine learning?

Search my notes for Python

Find information about team meetings
```

**Pro Tips:**
- Be specific when saving
- Include context in your saves
- Use natural language for searches
- The search is semantic (meaning-based)

---

### 🔍 Researcher - Your Information Hunter

**Best for:**
- Learning about new topics
- Finding external information
- Web research
- Staying updated

**Example Messages:**

```
Research artificial intelligence basics

Find information about renewable energy

Look up the latest SpaceX news

What is quantum computing?

Research climate change solutions

Find recent developments in AI
```

**Pro Tips:**
- Be specific about what you want to learn
- Can browse and summarize web pages
- Checks your brain first for existing knowledge
- Good for deep dives into topics

---

### ✍️ Writer - Your Content Creator

**Best for:**
- Drafting emails
- Formatting reports
- Creating polished content
- Synthesizing information

**Example Messages:**

```
Write a thank you email for my colleague

Draft a professional message about our project delay

Format this as a report: [your content]

Help me write a summary of my research

Create an email announcing our new product

Write a formal letter requesting information
```

**Pro Tips:**
- Specify the format you want
- Include relevant details
- Can pull from your knowledge base
- Great for professional communication

---

## ⚙️ Settings Explained

### 🔄 Auto-Route (Recommended: ON)
**ON:** AI automatically picks the best agent for your request
**OFF:** Uses your default agent for everything

**When to turn OFF:**
- You want all messages to go to one agent
- You're doing a specific task repeatedly
- You want full control

### 🎤 Voice Messages
**ON:** Can send voice notes (transcribed via Whisper)
**OFF:** Voice messages disabled

**Note:** Transcription uses OpenAI Whisper - very accurate!

### 🔔 Notifications
**ON:** Get detailed notifications when jobs complete
**OFF:** Minimal notifications

### 🎯 Default Agent
Choose which agent to use when Auto-Route is OFF:
- **Auto:** Smart routing (same as Auto-Route ON)
- **Archivist:** All messages save/search knowledge
- **Researcher:** All messages do research
- **Writer:** All messages format content

### ↩️ Max Retries
How many times to retry if a job fails:
- **1:** Fail fast
- **3:** Default, good balance
- **5:** Very persistent

---

## 🎤 Voice Message Tips

1. **Speak clearly** - Better transcription
2. **Keep it concise** - Under 1 minute ideal
3. **Include action** - "Save this..." or "Research..."
4. **Check transcript** - I'll show you what I heard

**Example Voice Messages:**
- "Save this thought: I need to follow up with John about the project"
- "Research the benefits of meditation"
- "Write an email thanking my team for their hard work"

---

## 💡 Best Practices

### For Saving Knowledge
```
✅ GOOD: "Save this: React is a JavaScript library for building UIs. Created by Facebook. Uses virtual DOM."

❌ TOO VAGUE: "Save: React is cool"
```

### For Searching
```
✅ GOOD: "What did I save about React and performance?"

❌ TOO VAGUE: "Find stuff"
```

### For Research
```
✅ GOOD: "Research the environmental impact of electric vehicles compared to gas cars"

❌ TOO VAGUE: "Tell me about cars"
```

### For Writing
```
✅ GOOD: "Write a professional email declining a meeting invitation politely, mentioning scheduling conflicts"

❌ TOO VAGUE: "Write an email"
```

---

## 🔍 Understanding Responses

### Job Queued
```
✅ Job Queued

🆔 Job ID: abc-123-xyz
📚 Agent: Archivist
⏳ Processing...

You'll be notified when complete!
```

**What this means:**
- Your request was received
- It's in the processing queue
- Workers will handle it soon
- You'll get a notification with results

### Task Completed
```
✅ Task Completed!

[Your results here]
```

### Task Failed
```
⚠️ Task Failed after 3 retries.
Job ID: abc-123
Error: [error details]

Please check logs or provide feedback.
```

**What to do:**
- Check `/status` to see if system is online
- Try rephrasing your request
- Check `/queue` to see if it's overloaded
- Contact admin if persistent

---

## 🐛 Troubleshooting

### "Not getting responses"
1. Check `/status` - is Redis connected?
2. Check `/queue` - is it too large?
3. Wait 30 seconds - workers might be busy
4. Try `/help` to test if bot is online

### "Wrong agent used"
1. Enable Auto-Route in `/settings`
2. Be more specific in your request
3. Mention the action: "save", "research", "write"

### "Voice not working"
1. Check `/settings` - is voice enabled?
2. Check file format (OGG/MP3 work best)
3. Keep messages under 2 minutes

### "Job failed multiple times"
1. Check `/status` for system health
2. Simplify your request
3. Try again in a few minutes
4. Check if it's too complex

---

## 📊 Understanding the System

### How Jobs Are Processed

```
You send message
    ↓
Bot receives & transcribes (if voice)
    ↓
AI routes to correct agent
    ↓
Job added to Redis queue
    ↓
Workers pick up job (2 running in parallel)
    ↓
Agent executes with tools
    ↓
Results sent back to you
```

### Processing Times
- **Simple saves:** 5-10 seconds
- **Searches:** 10-15 seconds
- **Research:** 20-30 seconds
- **Complex tasks:** 1-2 minutes

### Workers
- **2 workers** run in parallel
- Each can process 1 job at a time
- Jobs are processed FIFO (first in, first out)
- Failed jobs retry automatically

---

## 🎓 Advanced Usage

### Chaining Actions
The bot can chain multiple agents together (future feature):
```
"Research quantum computing and write a summary report"
↓ Researcher gathers info
↓ Writer formats it
```

### Context Awareness
Agents can access your knowledge base:
```
1. "Save: I'm working on Project Alpha"
2. "What am I working on?"
   ↓ Returns: "Project Alpha"
```

### Custom Preferences
Fine-tune behavior in `/settings`:
- Turn off notifications for quiet mode
- Set default agent for specific workflows
- Adjust retry count based on urgency

---

## 🔐 Privacy & Data

### What's Stored
- **Knowledge Base:** Text you explicitly save
- **Settings:** Your preferences
- **Job History:** For retry mechanism

### What's NOT Stored
- Your Telegram messages (unless saved)
- Voice recordings (deleted after transcription)
- Personal chat history

### Data Location
- **Redis:** Job queue (temporary)
- **SQLite:** Knowledge metadata
- **ChromaDB:** Vector embeddings

---

## 📞 Support

### System Status
Always check first:
```
/status
```

### Common Issues
See Troubleshooting section above

### Getting Help
```
/help - Built-in help
/agents - Agent details
```

---

## 🚀 Quick Command Reference

```
/start      - Welcome & overview
/help       - Detailed help
/settings   - Configure preferences
/status     - System health
/agents     - Agent info
/queue      - View queue
```

---

## 💎 Pro Tips

1. **Be Specific:** "Research AI ethics" > "Tell me about AI"

2. **Use Voice:** Great for capturing thoughts on-the-go

3. **Build Your Brain:** Save everything interesting - search later

4. **Check Settings:** Customize to your workflow

5. **Trust Auto-Route:** It's usually right about which agent to use

6. **Give Feedback:** If results aren't good, rephrase and try again

7. **Check Queue:** If slow, queue might be backed up

8. **Use Job IDs:** Track specific requests

9. **Combine Agents:** Save research results, then format them

10. **Regular Backups:** Ask admin to backup your knowledge base

---

**🎉 You're all set! Start by sending `/start` to your bot.**

**Need help? Send `/help` anytime.**

**Happy brain building! 🧠✨**
