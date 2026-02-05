import os
import asyncio
import json
import redis
import random
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

    # Check exact matches
    if text_lower in CASUAL_PATTERNS:
        return True

    # Check if message starts with casual pattern
    for pattern in CASUAL_PATTERNS:
        if text_lower.startswith(pattern):
            return True

    # Very short messages without keywords are likely casual
    if len(text.split()) <= 2 and not any(keyword in text_lower for keyword in ["save", "search", "research", "write", "find", "tell", "show", "what", "how", "why", "when"]):
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

async def route_intent(text: str) -> dict:
    prompt = f"""Analyze this user request and route it to the correct agent.
Available agents:
- content_saver: For saving URLs (web articles, tweets, links) and building knowledge graph. Use when user shares URLs or wants to save content from the web.
- archivist: For saving plain text information, thoughts, or searching existing knowledge.
- researcher: For simple web searches and quick lookups.
- writer: For formatting content, drafting emails, or writing reports.

User Request: {text}

Return JSON: {{"agent": "agent_name", "payload": {{...}}}}"""
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": "You are a routing system. Return ONLY JSON."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

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
🔴 Redis: {redis_status}
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
        # Determine agent and what will happen
        if settings['auto_route'] or settings['default_agent'] == 'auto':
            # Route intent using LLM
            routing = await route_intent(text)
            agent = routing.get("agent", "archivist")
            payload = routing.get("payload", {"text": text})
        else:
            # Use default agent
            agent = settings['default_agent']
            payload = {"text": text}

        payload["source"] = "telegram"
        payload["user_id"] = user_id

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
    ]

    await application.bot.set_my_commands(commands)
    print("✅ Bot menu configured with commands")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Set up bot menu
    asyncio.get_event_loop().run_until_complete(setup_bot_menu(application))

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("monitor", monitor_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("clear", clear_command))

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
