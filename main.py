import os
import asyncio
import json
import redis
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from openai import OpenAI
from common.config import TELEGRAM_TOKEN, OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER, REDIS_URL, TASK_QUEUE
from common.contracts import Job, JobStatus

# User settings stored in Redis
USER_SETTINGS_KEY = "user_settings:{user_id}"
DEFAULT_SETTINGS = {
    "auto_route": True,
    "voice_enabled": True,
    "notifications": True,
    "default_agent": "auto",
    "max_retries": 3
}

# 30+ thinking message variations
THINKING_MESSAGES = [
    "🧠 Processing your request...",
    "🤔 Analyzing your message...",
    "⚡ Working on it...",
    "🎯 Getting that done for you...",
    "✨ Making the magic happen...",
    "🔍 Looking into this...",
    "💭 Thinking deeply about this...",
    "🚀 Launching your request...",
    "🎨 Crafting a response...",
    "🌟 On it right away...",
    "🔮 Consulting the brain...",
    "📚 Diving into the knowledge...",
    "🎪 Performing some AI wizardry...",
    "🌊 Riding the neural waves...",
    "🎵 Orchestrating the agents...",
    "🔬 Running the algorithms...",
    "🎭 Setting the stage...",
    "🌈 Painting with data...",
    "⚙️ Spinning up the engines...",
    "🎯 Targeting the solution...",
    "🧩 Piecing it together...",
    "🌠 Stargazing through the data...",
    "🎪 Juggling the bytes...",
    "🔥 Firing up the neurons...",
    "💡 Having a lightbulb moment...",
    "🎬 Directing the AI orchestra...",
    "🌪️ Whirling through the logic...",
    "🎨 Sketching out the answer...",
    "🚁 Taking a bird's eye view...",
    "🔎 Magnifying the details...",
    "🌟 Connecting the stars...",
    "🎲 Rolling the neural dice...",
    "🎪 Putting on the show...",
    "🌊 Surfing the data streams...",
]

# Casual conversation patterns that shouldn't be queued
CASUAL_PATTERNS = [
    "hi", "hello", "hey", "yo", "sup", "what's up", "whats up",
    "good morning", "good afternoon", "good evening", "good night",
    "how are you", "how r u", "hows it going", "how's it going",
    "thanks", "thank you", "thx", "ty",
    "ok", "okay", "k", "cool", "nice", "great", "awesome",
    "bye", "goodbye", "see you", "cya", "later",
]

if LLM_PROVIDER == "deepseek":
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    MODEL_NAME = "deepseek-chat"
else:
    client = OpenAI(api_key=OPENAI_API_KEY)
    MODEL_NAME = "gpt-4o-mini"

r = redis.from_url(REDIS_URL)

def get_user_settings(user_id: int) -> dict:
    """Get user settings from Redis"""
    key = USER_SETTINGS_KEY.format(user_id=user_id)
    settings_json = r.get(key)
    if settings_json:
        return json.loads(settings_json)
    return DEFAULT_SETTINGS.copy()

def save_user_settings(user_id: int, settings: dict):
    """Save user settings to Redis"""
    key = USER_SETTINGS_KEY.format(user_id=user_id)
    r.set(key, json.dumps(settings))

def is_casual_message(text: str) -> bool:
    """Check if message is casual conversation vs actionable request"""
    text_lower = text.lower().strip()

    # URLs are never casual - always actionable
    if re.search(r'https?://', text_lower):
        print(f"🔗 URL detected in is_casual_message, marking as actionable")
        return False

    # Action keywords override any casual pattern match
    action_keywords = [
        "save", "search", "research", "write", "find", "tell", "show",
        "what", "how", "why", "when", "where", "who", "explain",
        "summarize", "draft", "format", "help", "look up", "investigate",
        "remember", "note", "store", "browse", "analyze",
        "create", "build", "generate", "code", "design", "model",
        "scaffold", "implement", "develop", "architecture"
    ]
    if any(keyword in text_lower for keyword in action_keywords):
        return False

    # Check exact matches only (no startswith - too many false positives)
    if text_lower in CASUAL_PATTERNS:
        return True

    # Single-word messages without action keywords are likely casual
    # (2-word messages like "Docker help" or "search Python" should be routed)
    if len(text.split()) == 1:
        return True

    return False

async def get_casual_response(text: str) -> str:
    """Get AI-generated response for casual messages"""
    prompt = f"""You are Assistant Brain OS, a friendly AI assistant that helps users manage knowledge, research topics, and write content.

The user sent a casual message: "{text}"

Respond naturally and conversationally, as a helpful AI assistant would. Keep it brief (2-3 sentences).
If appropriate, gently remind them what you can do (save knowledge, research, or write), but don't be pushy.
Be warm, friendly, and natural. Match their energy level.

Respond naturally:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a friendly, conversational AI assistant. Keep responses natural, brief, and engaging."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # More creative for conversation
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback if LLM fails
        return f"😊 {text}! I'm here to help with saving knowledge, research, or writing. What can I do for you?"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with bot overview"""
    welcome_text = """🧠 **Welcome to Assistant Brain OS!**

I'm your intelligent second brain, powered by AI agents that can:

📚 **Save & Search Knowledge** (Archivist)
→ Save notes, thoughts, and information
→ Search through your knowledge base semantically
→ Build your personal knowledge repository

🔍 **Research Topics** (Researcher)
→ Deep dive into any topic
→ Browse and extract web content
→ Find and synthesize information

✍️ **Format Content** (Writer)
→ Draft emails and reports
→ Format and structure your writing
→ Synthesize information beautifully

---

**🎯 Quick Start:**

1️⃣ **Save something:**
   "Save this: Machine learning is fascinating"

2️⃣ **Search your brain:**
   "What did I save about machine learning?"

3️⃣ **Research a topic:**
   "Research quantum computing basics"

4️⃣ **Format content:**
   "Write an email thanking my team"

**🎤 Voice Support:** Send voice messages - I'll transcribe and process them!

---

**📋 Menu Commands Available:**
Use the menu button or type:
/help - Detailed help and examples
/settings - Configure preferences
/status - Check system status
/agents - Learn about agents
/queue - View pending jobs

**💬 Just start chatting! I'll figure out what you need.**
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

def route_deterministic(text: str) -> str:
    """Route user message to the correct agent using pattern matching. No LLM call.

    Returns agent name string. Fast, reliable, zero network calls.
    """
    text_lower = text.lower().strip()

    # 1. URLs → content_saver (already handled upstream, but double-check)
    if re.search(r'https?://', text_lower):
        return "content_saver"

    # 2. Code generation keywords
    code_patterns = [
        r'\b(create|build|generate|scaffold|implement)\b.*\b(project|app|code|script|model|schema|api)\b',
        r'\b(code|program|develop)\b',
        r'\bdata\s+model\b', r'\bstar\s+schema\b', r'\bload\s+script\b',
    ]
    for pattern in code_patterns:
        if re.search(pattern, text_lower):
            return "coder"

    # 3. Writing/formatting keywords
    write_patterns = [
        r'\b(write|draft|compose)\b.*\b(email|letter|report|message|post|article|essay)\b',
        r'\b(format|reformat|rewrite)\b',
        r'\bdraft\s+(a|an|the|me)\b',
    ]
    for pattern in write_patterns:
        if re.search(pattern, text_lower):
            return "writer"

    # 4. Explicit research / web lookup
    research_patterns = [
        r'\bresearch\b', r'\binvestigate\b',
        r'\blook\s*up\b', r'\bsearch\s+the\s+web\b',
        r'\bgoogle\b', r'\bweb\s+search\b',
    ]
    for pattern in research_patterns:
        if re.search(pattern, text_lower):
            return "researcher"

    # 5. Explicit save/store intent → archivist
    save_patterns = [
        r'\bsave\b', r'\bremember\b', r'\bstore\b',
        r'\bnote\s*(this|that|:)\b', r'\bkeep\s*(this|that)\b',
        r'\badd\s*(this|that|to)\b',
    ]
    for pattern in save_patterns:
        if re.search(pattern, text_lower):
            return "archivist"

    # 6. Explicit knowledge base search → archivist
    kb_patterns = [
        r'\b(my|your)\s+(notes?|knowledge|brain|saved|entries)\b',
        r'\bwhat\s+(did|do)\s+(i|we|you)\s+(save|have|know)\b',
        r'\bsearch\s+(my|the)\s+(brain|knowledge|notes)\b',
        r'\bfind\s+(my|in\s+my)\b',
    ]
    for pattern in kb_patterns:
        if re.search(pattern, text_lower):
            return "archivist"

    # 7. General questions → researcher (it checks brain first, then web)
    question_patterns = [
        r'^(what|where|when|who|how|why|which|is|are|was|were|can|could|do|does|did|will|would|should)\b',
        r'\?$',
        r'\b(explain|tell\s+me|describe)\b',
    ]
    for pattern in question_patterns:
        if re.search(pattern, text_lower):
            return "researcher"

    # 8. Short messages without clear intent → archivist (search mode)
    if len(text.split()) <= 5:
        return "archivist"

    # 9. Default: longer text is probably something to save
    return "archivist"

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed help and examples"""
    help_text = """📖 **Assistant Brain OS - Detailed Help**

**🤖 Available Agents:**

**1. Content Saver** 💾
Your Obsidian-style knowledge curator
• Just share any URL: "https://article.com/interesting-post"
• Share tweets: "https://twitter.com/user/status/123"
• Save notes: "Remember this important insight..."
• Build your connected knowledge graph automatically

**2. Archivist** 📚
Manages and searches your knowledge base
• "Search my brain for python notes"
• "What did I save about meetings?"
• "Find content about AI"
• "Show me recent saves"

**3. Researcher** 🔍
Quick web searches and lookups
• "What's the weather like today?"
• "Quick search: Python tutorials"
• "Look up SpaceX news"

**4. Writer** ✍️
Formats and creates content
• "Write an email to thank my colleague"
• "Format this as a report: [your text]"
• "Draft a professional message about..."
• "Help me write a summary of..."

---

**⚙️ Features:**

🎤 **Voice Messages:** Send voice notes and I'll transcribe them automatically

🔄 **Auto-Routing:** I intelligently detect which agent to use

📊 **Job Tracking:** Every request gets a unique Job ID

♻️ **Auto-Retry:** Failed jobs retry up to 3 times

---

**📋 Commands:**

/start - Welcome message
/help - This help message
/settings - Configure preferences
/status - System status
/agents - Agent details
/queue - View pending jobs
/clear - Clear your queue

**💡 Tips:**

• Be specific in your requests
• Voice messages are transcribed via Whisper
• Jobs are processed asynchronously
• Check /status if you don't get a response

Need more help? Just ask: "How do I use the researcher?"
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu with inline keyboard"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    keyboard = [
        [
            InlineKeyboardButton(
                f"🔄 Auto-Route: {'✅' if settings['auto_route'] else '❌'}",
                callback_data='toggle_auto_route'
            )
        ],
        [
            InlineKeyboardButton(
                f"🎤 Voice: {'✅' if settings['voice_enabled'] else '❌'}",
                callback_data='toggle_voice'
            )
        ],
        [
            InlineKeyboardButton(
                f"🔔 Notifications: {'✅' if settings['notifications'] else '❌'}",
                callback_data='toggle_notifications'
            )
        ],
        [
            InlineKeyboardButton("🎯 Default Agent", callback_data='set_default_agent')
        ],
        [
            InlineKeyboardButton("↩️ Retries: " + str(settings['max_retries']), callback_data='set_retries')
        ],
        [
            InlineKeyboardButton("🔄 Reset to Defaults", callback_data='reset_settings')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    settings_text = f"""⚙️ **Your Settings**

🔄 Auto-Route: {'Enabled' if settings['auto_route'] else 'Disabled'}
🎤 Voice Messages: {'Enabled' if settings['voice_enabled'] else 'Disabled'}
🔔 Notifications: {'Enabled' if settings['notifications'] else 'Disabled'}
🎯 Default Agent: {settings['default_agent'].title()}
↩️ Max Retries: {settings['max_retries']}

*Tap buttons below to change settings:*
"""

    await update.message.reply_text(settings_text, parse_mode='Markdown', reply_markup=reply_markup)

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings button clicks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    if query.data == 'toggle_auto_route':
        settings['auto_route'] = not settings['auto_route']
        save_user_settings(user_id, settings)
        await query.edit_message_text("✅ Auto-route setting updated! Use /settings to see changes.")

    elif query.data == 'toggle_voice':
        settings['voice_enabled'] = not settings['voice_enabled']
        save_user_settings(user_id, settings)
        await query.edit_message_text("✅ Voice setting updated! Use /settings to see changes.")

    elif query.data == 'toggle_notifications':
        settings['notifications'] = not settings['notifications']
        save_user_settings(user_id, settings)
        await query.edit_message_text("✅ Notification setting updated! Use /settings to see changes.")

    elif query.data == 'set_default_agent':
        keyboard = [
            [InlineKeyboardButton("🤖 Auto (Smart Routing)", callback_data='agent_auto')],
            [InlineKeyboardButton("📚 Archivist", callback_data='agent_archivist')],
            [InlineKeyboardButton("🔍 Researcher", callback_data='agent_researcher')],
            [InlineKeyboardButton("✍️ Writer", callback_data='agent_writer')],
            [InlineKeyboardButton("⬅️ Back", callback_data='back_to_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose your default agent:", reply_markup=reply_markup)

    elif query.data.startswith('agent_'):
        agent = query.data.replace('agent_', '')
        settings['default_agent'] = agent
        save_user_settings(user_id, settings)
        await query.edit_message_text(f"✅ Default agent set to: {agent.title()}! Use /settings to see changes.")

    elif query.data == 'set_retries':
        keyboard = [
            [InlineKeyboardButton("1 retry", callback_data='retries_1')],
            [InlineKeyboardButton("3 retries (default)", callback_data='retries_3')],
            [InlineKeyboardButton("5 retries", callback_data='retries_5')],
            [InlineKeyboardButton("⬅️ Back", callback_data='back_to_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose max retries for failed jobs:", reply_markup=reply_markup)

    elif query.data.startswith('retries_'):
        retries = int(query.data.replace('retries_', ''))
        settings['max_retries'] = retries
        save_user_settings(user_id, settings)
        await query.edit_message_text(f"✅ Max retries set to: {retries}! Use /settings to see changes.")

    elif query.data == 'reset_settings':
        save_user_settings(user_id, DEFAULT_SETTINGS.copy())
        await query.edit_message_text("✅ Settings reset to defaults! Use /settings to see changes.")

    elif query.data == 'back_to_settings':
        # Re-show settings menu
        await query.edit_message_text("Use /settings to see the menu again.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status"""
    try:
        # Check Redis
        redis_status = "✅ Connected" if r.ping() else "❌ Disconnected"
        queue_size = r.llen(TASK_QUEUE)

        # Check user stats
        user_id = update.effective_user.id
        settings = get_user_settings(user_id)

        status_text = f"""📊 **System Status**

**Backend Services:**
{'🟢' if r.ping() else '🔴'} Redis: {redis_status}
📦 Queue Size: {queue_size} jobs

**Your Settings:**
🎯 Default Agent: {settings['default_agent'].title()}
🔄 Auto-Route: {'Enabled' if settings['auto_route'] else 'Disabled'}
🎤 Voice: {'Enabled' if settings['voice_enabled'] else 'Disabled'}

**Configuration:**
🤖 LLM Provider: {LLM_PROVIDER.upper()}
🧠 Model: {MODEL_NAME}

**System:** Online and ready! 🟢

Use /queue to see your pending jobs.
"""
        await update.message.reply_text(status_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error checking status: {str(e)}")

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed agent information"""
    agents_text = """🤖 **Available Agents**

**📚 ARCHIVIST**
*Your Knowledge Manager*

**What it does:**
• Saves information to your brain
• Searches stored knowledge semantically
• Manages tags and metadata
• Builds your personal knowledge base

**Tools:**
• save_knowledge() - Store with tags
• search_knowledge() - Semantic search

**Example requests:**
• "Save this: AI ethics is important"
• "Remember: Budget meeting Friday"
• "Search for notes about Python"
• "What did I save about meetings?"

---

**🔍 RESEARCHER**
*Your Information Hunter*

**What it does:**
• Researches topics deeply
• Browses web pages
• Extracts and analyzes content
• Finds external information

**Tools:**
• search_brain() - Check existing knowledge
• search_web() - Search the internet
• browse_page() - Extract from URLs

**Example requests:**
• "Research machine learning basics"
• "Find info about climate change"
• "Look up SpaceX latest news"
• "Browse example.com and summarize"

---

**✍️ WRITER**
*Your Content Creator*

**What it does:**
• Formats and structures content
• Drafts emails and reports
• Synthesizes information
• Creates polished writing

**Tools:**
• get_context() - Fetch relevant knowledge

**Example requests:**
• "Write a thank you email"
• "Format this as a report"
• "Draft a professional message about..."
• "Help me write a summary"

---

**🛠️ CODER**
*Your Code Generator*

**What it does:**
• Generates complete projects from skill templates
• Builds data models, load scripts, and configurations
• Creates documentation alongside code
• Uses domain-specific best practices

**Tools:**
• find_skills() - Discover relevant skill files
• load_skill() - Read templates and patterns
• create_plan() - Plan the execution steps
• write_file() - Generate project files
• write_summary() - Finalize with README
• search_knowledge() - Check existing context

**Example requests:**
• "Create a Qlik data model for e-commerce"
• "Build a star schema for sales analytics"
• "Generate incremental load scripts for orders"

---

💡 **Tip:** I automatically detect which agent to use, but you can override this in /settings
"""
    await update.message.reply_text(agents_text, parse_mode='Markdown')

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's queue status"""
    queue_size = r.llen(TASK_QUEUE)

    queue_text = f"""📋 **Queue Status**

**Global Queue:** {queue_size} jobs pending

Jobs are processed by 2 worker instances in parallel.

**Processing Time:**
• Simple tasks: ~5-10 seconds
• Research tasks: ~20-30 seconds
• Complex tasks: ~1-2 minutes

If a job takes too long, it will retry up to {get_user_settings(update.effective_user.id)['max_retries']} times.

Use /status to check if the system is running.
"""
    await update.message.reply_text(queue_text, parse_mode='Markdown')

async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Real-time monitoring of jobs and agent activity"""
    try:
        queue_size = r.llen(TASK_QUEUE)

        # Get active jobs (jobs currently being processed)
        active_jobs = []
        processing_keys = r.keys("job:processing:*")
        for key in processing_keys[:5]:  # Show up to 5 active jobs
            job_data = r.get(key)
            if job_data:
                try:
                    job_info = json.loads(job_data)
                    active_jobs.append(job_info)
                except:
                    pass

        # Get recent completions (last 10 minutes)
        recent_completed = []
        completed_keys = r.keys("job:completed:*")
        for key in completed_keys[-5:]:  # Show last 5 completed
            job_data = r.get(key)
            if job_data:
                try:
                    job_info = json.loads(job_data)
                    recent_completed.append(job_info)
                except:
                    pass

        # Get agent activity logs
        agent_activity = []
        activity_keys = r.keys("agent:activity:*")
        for key in activity_keys[-5:]:  # Last 5 activities
            activity = r.get(key)
            if activity:
                agent_activity.append(activity.decode('utf-8'))

        # Build monitoring message
        monitor_text = f"""🔍 **Real-Time Monitoring**

📊 **Queue Status:**
• Pending jobs: {queue_size}
• Worker instances: 2 (parallel processing)
• Max concurrent: 2 tasks at once

⚡ **Currently Processing:**"""

        if active_jobs:
            for job in active_jobs:
                agent = job.get('agent', 'unknown')
                started = job.get('started', 'unknown')
                monitor_text += f"\n• 🔄 {agent.title()} Agent (started {started}s ago)"
        else:
            monitor_text += "\n• ✅ No active jobs (workers idle)"

        monitor_text += "\n\n✅ **Recent Completions:**"
        if recent_completed:
            for job in recent_completed:
                agent = job.get('agent', 'unknown')
                duration = job.get('duration', 0)
                monitor_text += f"\n• ✓ {agent.title()} Agent ({duration}s)"
        else:
            monitor_text += "\n• No recent completions"

        if agent_activity:
            monitor_text += "\n\n🔧 **Recent Agent Activity:**"
            for activity in agent_activity:
                monitor_text += f"\n• {activity}"

        monitor_text += "\n\n💡 **Tips:**"
        monitor_text += "\n• Use /queue to see pending jobs"
        monitor_text += "\n• Use /status for system health"
        monitor_text += "\n• Check logs: `pm2 logs brain-worker`"

        await update.message.reply_text(monitor_text, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Monitoring error: {str(e)}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the task queue (admin only or confirmation)"""
    queue_size = r.llen(TASK_QUEUE)
    await update.message.reply_text(
        f"⚠️ Queue has {queue_size} jobs.\n\n"
        "Note: You can only clear your own failed jobs. Contact admin for full queue clear."
    )

async def issues_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent unfulfilled requests."""
    try:
        from common.goal_tracker import GoalTracker
        from common.database import db
        tracker = GoalTracker(db.conn, r)
        issues = tracker.get_recent_issues(limit=5)

        if not issues:
            await update.message.reply_text("No recent issues - everything is working!")
            return

        text = "Recent Unfulfilled Requests:\n\n"
        for i, issue in enumerate(issues, 1):
            text += f"{i}. [{issue['issue_type']}] {issue['user_input'][:80]}\n"
            text += f"   Agent: {issue['agent']} | {issue['created_at'][:10]}\n"
            text += f"   Reason: {issue['fulfillment_reason']}\n\n"

        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Error loading issues: {str(e)}")


async def fulfillment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show fulfillment rate statistics."""
    try:
        from common.goal_tracker import GoalTracker
        from common.database import db
        tracker = GoalTracker(db.conn, r)
        stats = tracker.get_stats(days=7)

        text = f"Goal Fulfillment (Last 7 Days)\n\n"
        text += f"Total requests: {stats['total']}\n"
        text += f"Fulfilled: {stats['fulfilled']} ({stats['fulfillment_rate']:.0%})\n"
        text += f"Unfulfilled: {stats['unfulfilled']}\n\n"

        if stats['per_agent']:
            text += "Per Agent:\n"
            for agent, agent_stats in stats['per_agent'].items():
                text += f"  {agent}: {agent_stats['fulfilled']}/{agent_stats['total']} ({agent_stats['rate']:.0%})\n"

        if stats['common_issues']:
            text += "\nCommon Issues:\n"
            for issue_type, count in stats['common_issues'].items():
                text += f"  {issue_type}: {count}\n"

        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Error loading stats: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text and voice messages with smart routing and feedback"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    text = ""

    # Always use OpenAI for Whisper regardless of LLM_PROVIDER
    whisper_client = OpenAI(api_key=OPENAI_API_KEY)

    # Handle voice messages
    if update.message.voice:
        if not settings['voice_enabled']:
            await update.message.reply_text(
                "🎤 Voice messages are disabled in your settings.\n\n"
                "Use /settings to enable them, or send a text message instead!"
            )
            return

        # Show transcribing message
        transcribing_msg = await update.message.reply_text("🎤 Transcribing your voice message...")

        try:
            file = await context.bot.get_file(update.message.voice.file_id)
            os.makedirs("temp", exist_ok=True)
            file_path = f"temp/{update.message.voice.file_id}.ogg"
            await file.download_to_drive(file_path)

            with open(file_path, "rb") as audio_file:
                transcript = whisper_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            text = transcript.text

            # Update with transcript
            await transcribing_msg.edit_text(
                f"🎤 **Transcribed:**\n\n_{text}_\n\n"
                f"Now processing...",
                parse_mode='Markdown'
            )
            os.remove(file_path)
        except Exception as e:
            await transcribing_msg.edit_text(f"❌ Error transcribing voice: {str(e)}")
            return
    else:
        text = update.message.text

    # Check if this is casual conversation - respond with AI-generated message
    if is_casual_message(text):
        # Show a thinking message
        thinking_msg = await update.message.reply_text(random.choice(["💬 Thinking...", "💭 One moment...", "🤔 Let me respond..."]))
        response = await get_casual_response(text)
        await thinking_msg.edit_text(response)
        return

    # Show random thinking message
    thinking_msg = await update.message.reply_text(random.choice(THINKING_MESSAGES))

    try:
        # Determine agent — deterministic routing, no LLM call
        if settings['default_agent'] not in ('auto', 'archivist', 'researcher', 'writer', 'coder', 'content_saver'):
            agent = route_deterministic(text)
        elif settings['auto_route'] or settings['default_agent'] == 'auto':
            agent = route_deterministic(text)
        else:
            agent = settings['default_agent']

        print(f"🔀 Routed to: {agent} | Text: {text[:60]}")

        # Build payload — ALWAYS include original text
        payload = {"text": text}
        payload["source"] = "telegram"
        payload["user_id"] = user_id

        # Classify goal for tracking
        from common.goal_tracker import GoalTracker
        payload["goal_type"] = GoalTracker.classify_goal(agent, text)

        # Natural acknowledgment messages based on agent type
        natural_responses = {
            "content_saver": [
                "💾 I'll extract and save that for you!",
                "📚 Adding this to your knowledge graph...",
                "🔖 Let me save this content...",
                "✨ I'll curate that and add it to your collection!",
                "📝 Extracting and organizing this content..."
            ],
            "archivist": [
                "Got it! I'll save that to your knowledge base.",
                "Perfect, I'll add that to your brain.",
                "Let me save that for you.",
                "I'll remember that!"
            ] if "save" in text.lower() or "remember" in text.lower() else [
                "Let me check what we have on that...",
                "I'll search the knowledge base for you.",
                "Let me see what I can find...",
                "Checking what we know about that..."
            ],
            "researcher": [
                "Interesting topic! Let me research that for you.",
                "I'll look into that and see what I can find.",
                "Let me dig into this...",
                "On it - researching now!",
                "Great question! Let me find some information on that."
            ],
            "writer": [
                "I'll help you with that!",
                "Let me draft something for you.",
                "I can help format that.",
                "I'll work on that for you!"
            ],
            "coder": [
                "I'll build that for you! Setting up the project now...",
                "On it! Let me find the right skills and generate the code.",
                "Starting the coding agent - I'll create all the files for you.",
                "Let me architect and code that up for you!"
            ]
        }

        # Get natural response for this agent
        responses = natural_responses.get(agent, ["I'm on it!"])
        natural_message = random.choice(responses)

        # Create Job
        job = Job(
            current_agent=agent,
            payload=payload,
            max_retries=settings['max_retries']
        )

        # Push to Redis
        r.lpush(TASK_QUEUE, job.model_dump_json())

        # Send natural acknowledgment (delete thinking message, send new one)
        await thinking_msg.delete()
        await update.message.reply_text(natural_message)

    except Exception as e:
        await thinking_msg.edit_text(
            f"❌ **Error**\n\n"
            f"Something went wrong: {str(e)}\n\n"
            f"Try rephrasing your request or use /help for examples."
        )

async def setup_bot_menu(application: Application):
    """Set up the Telegram bot menu with commands"""
    commands = [
        BotCommand("start", "🏠 Welcome & overview"),
        BotCommand("help", "📖 Detailed help & examples"),
        BotCommand("settings", "⚙️ Configure preferences"),
        BotCommand("status", "📊 System status check"),
        BotCommand("monitor", "🔍 Real-time agent activity"),
        BotCommand("agents", "🤖 Learn about agents"),
        BotCommand("queue", "📋 View pending jobs"),
        BotCommand("issues", "🐛 View unfulfilled requests"),
        BotCommand("fulfillment", "📈 Goal fulfillment stats"),
    ]

    await application.bot.set_my_commands(commands)
    print("✅ Bot menu configured with commands")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Set up bot menu via post_init hook (avoids deprecated event loop usage)
    async def post_init(app):
        await setup_bot_menu(app)

    application.post_init = post_init

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("monitor", monitor_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("issues", issues_command))
    application.add_handler(CommandHandler("fulfillment", fulfillment_command))

    # Callback query handler for settings buttons
    application.add_handler(CallbackQueryHandler(settings_callback))

    # Message handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))

    print("🧠 Assistant Brain Bot started...")
    print(f"📡 LLM Provider: {LLM_PROVIDER}")
    print(f"🤖 Model: {MODEL_NAME}")
    print("✅ Ready to receive messages!")
    print("💬 Bot menu configured - users can see commands via '/' or menu button")
    application.run_polling()

if __name__ == "__main__":
    main()
