"""Deterministic message routing shared between Telegram bot and web backend."""
import re
import random


# Casual conversation patterns that shouldn't be queued to agents
CASUAL_PATTERNS = [
    "hi", "hello", "hey", "yo", "sup", "what's up", "whats up",
    "good morning", "good afternoon", "good evening", "good night",
    "how are you", "how r u", "hows it going", "how's it going",
    "thanks", "thank you", "thx", "ty",
    "ok", "okay", "k", "cool", "nice", "great", "awesome",
    "bye", "goodbye", "see you", "cya", "later",
]

# Action keywords that override casual detection
_ACTION_KEYWORDS = [
    "save", "search", "research", "write", "find", "tell", "show",
    "what", "how", "why", "when", "where", "who", "explain",
    "summarize", "draft", "format", "help", "look up", "investigate",
    "remember", "note", "store", "browse", "analyze",
    "create", "build", "generate", "code", "design", "model",
    "scaffold", "implement", "develop", "architecture",
    "remind", "todo", "task", "journal", "diary",
]

# Casual response templates (no LLM needed for basic greetings)
_CASUAL_RESPONSES = {
    "greeting": [
        "Hey! What can I help you with today?",
        "Hi there! Need me to save something, look something up, or research a topic?",
        "Hey! I'm ready to help — what's on your mind?",
    ],
    "thanks": [
        "Anytime! Let me know if you need anything else.",
        "Happy to help! What's next?",
        "You're welcome! Anything else I can do?",
    ],
    "farewell": [
        "See you later! Your brain will be here when you need it.",
        "Catch you later! Everything's saved and ready for next time.",
        "Bye! Come back anytime.",
    ],
    "affirmative": [
        "Got it! Need anything else?",
        "Cool! Let me know if there's anything else.",
        "Alright! I'm here if you need me.",
    ],
    "default": [
        "I'm here! Want me to save some knowledge, research a topic, or help with a task?",
        "Hey! I can help with saving notes, researching things, managing tasks, or writing. What do you need?",
    ],
}


def is_casual(text: str) -> bool:
    """Check if message is casual conversation vs actionable request."""
    text_lower = text.lower().strip()

    # URLs are never casual
    if re.search(r'https?://', text_lower):
        return False

    # Action keywords override casual
    if any(keyword in text_lower for keyword in _ACTION_KEYWORDS):
        return False

    # Exact match against known casual patterns
    if text_lower in CASUAL_PATTERNS:
        return True

    # Single-word messages without action keywords are likely casual
    if len(text.split()) == 1:
        return True

    return False


def get_casual_response(text: str) -> str:
    """Get a casual response without LLM. Fast and deterministic."""
    text_lower = text.lower().strip()

    if text_lower in ("hi", "hello", "hey", "yo", "sup", "what's up", "whats up",
                       "good morning", "good afternoon", "good evening"):
        return random.choice(_CASUAL_RESPONSES["greeting"])
    elif text_lower in ("thanks", "thank you", "thx", "ty"):
        return random.choice(_CASUAL_RESPONSES["thanks"])
    elif text_lower in ("bye", "goodbye", "see you", "cya", "later", "good night"):
        return random.choice(_CASUAL_RESPONSES["farewell"])
    elif text_lower in ("ok", "okay", "k", "cool", "nice", "great", "awesome"):
        return random.choice(_CASUAL_RESPONSES["affirmative"])
    else:
        return random.choice(_CASUAL_RESPONSES["default"])


def route_deterministic(text: str) -> str:
    """Route user message to the correct agent using pattern matching. No LLM call.

    Returns agent name string. Fast, reliable, zero network calls.
    """
    text_lower = text.lower().strip()

    # 0. Casual messages -> "casual" (handled inline, not queued)
    if is_casual(text_lower):
        return "casual"

    # 1. URLs -> content_saver (already handled upstream, but double-check)
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

    # 5. Journal / diary entries -> journal
    journal_patterns = [
        r'^journal\s*(?:entry)?\s*[:;-]',
        r'^diary\s*(?:entry)?\s*[:;-]',
        r'^daily\s*(?:log|note|entry)\s*[:;-]',
        r'^log\s*[:;-]',
        r'\b(?:my|show|view|read|list|see|recent|last)\s*(?:journal|diary)\s*(?:entries?)?\b',
        r'\b(?:journal|diary)\s*(?:entries|history|list)\b',
        r'\bwhat\s+did\s+i\s+(?:write|journal|log)\b',
    ]
    for pattern in journal_patterns:
        if re.search(pattern, text_lower):
            return "journal"

    # 6. Tasks / reminders / to-dos -> task_manager
    task_patterns = [
        r'\bremind\s+me\b',
        r'\b(?:add\s+)?(?:a\s+)?(?:todo|to-?do)\b',
        r'\b(?:add\s+)?(?:a\s+)?task\b',
        r'\bset\s+(?:a\s+)?reminder\b',
        r'\bdon\'?t\s+(?:let\s+me\s+)?forget\b',
        r'\b(?:my|show|list|view|see|pending|upcoming)\s*(?:tasks?|todos?|to-?dos?|reminders?)\b',
        r'\b(?:tasks?|todos?|to-?dos?|reminders?)\s*(?:list|pending|upcoming|due)\b',
        r'\b(?:done|finished|completed?|check\s*off|mark\s*done)\s+(?:with\s+)?(?:#?\d+|task|todo)\b',
        r'\bdeadline\b',
        r'\bdue\s+(?:date|on|by)\b',
        r'\bi\s+(?:need|have|want|must)\s+to\b.*\b(?:by|before|on|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    ]
    for pattern in task_patterns:
        if re.search(pattern, text_lower):
            return "task_manager"

    # 7. Explicit save/store intent -> archivist
    save_patterns = [
        r'\bsave\b', r'\bremember\b', r'\bstore\b',
        r'\bnote\s*(this|that|:)\b', r'\bkeep\s*(this|that)\b',
        r'\badd\s*(this|that|to)\b',
    ]
    for pattern in save_patterns:
        if re.search(pattern, text_lower):
            return "archivist"

    # 8. Explicit knowledge base search -> archivist
    kb_patterns = [
        r'\b(my|your)\s+(notes?|knowledge|brain|saved|entries)\b',
        r'\bwhat\s+(did|do)\s+(i|we|you)\s+(save|have|know)\b',
        r'\bsearch\s+(my|the)\s+(brain|knowledge|notes)\b',
        r'\bfind\s+(my|in\s+my)\b',
        r'\bwhat\s+did\s+i\s+(save|write|note|log|add|store)\b',
        r'\bdo\s+i\s+have\s+(any|something|anything)\b',
        r'\bi\s+(saved|wrote|noted|added)\b.*\b(about|on)\b',
        r'\bmy\s+(stuff|things|entries|records)\b',
    ]
    for pattern in kb_patterns:
        if re.search(pattern, text_lower):
            return "archivist"

    # 9. General questions -> researcher (it checks brain first, then web)
    question_patterns = [
        r'^(what|where|when|who|how|why|which|is|are|was|were|can|could|do|does|did|will|would|should)\b',
        r'\?$',
        r'\b(explain|tell\s+me|describe)\b',
    ]
    for pattern in question_patterns:
        if re.search(pattern, text_lower):
            return "researcher"

    # 10. Short messages without clear intent -> archivist (search mode)
    if len(text.split()) <= 5:
        return "archivist"

    # 11. Default: longer text is probably something to save
    return "archivist"
