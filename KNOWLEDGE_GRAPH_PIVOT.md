# Knowledge Graph Pivot - Obsidian-Style System

## What Changed?

We've pivoted from heavy multi-source research to an **Obsidian-style knowledge graph** system focused on content curation and connected knowledge.

## Why?

Based on your feedback:
1. Deep research wasn't working as intended
2. You wanted to return to the original Obsidian knowledge graph vision
3. You wanted to save links, tweets, and build connections
4. Concerns about cost (knowledge graphs can be expensive with cloud solutions)

## New Architecture

### 1. Content Saver Agent (Primary)

**What it does:**
- Saves website URLs with automatic content extraction
- Handles Twitter/X links (basic extraction, expandable with API)
- Stores plain text notes with tags
- **Automatically builds knowledge graph connections**

**How to use:**
```
Just share a URL:
"https://interesting-article.com/ai-trends"

Or save a note:
"Remember: Knowledge graphs are powerful for PKM"
```

**Features:**
- Auto-extracts title, content, metadata
- Generates relevant tags automatically
- Creates connections to related content
- Shows you how many notes are auto-linked

### 2. Knowledge Graph (NetworkX)

**Structure:**
- **Nodes**: Your saved content (articles, tweets, notes)
- **Edges**: Relationships between content
  - `related-to`: Auto-linked by shared tags
  - `mentions`: One note mentions another
  - `cites`: One note cites another
  - `builds-on`: Extends ideas from another note

**Auto-linking:**
When you save content with tags like `["ai", "machine-learning"]`, the system automatically:
1. Finds other notes with overlapping tags
2. Creates bidirectional "related-to" edges
3. Shows you connection count when saving

**Visualization:**
- See connections between notes
- Navigate your knowledge graph
- Find related content through links
- Track how your knowledge connects

**Cost:** $0 (runs locally, no API, persists to `data/knowledge_graph.pkl`)

### 3. Enhanced Search with Reranking

**Jina Reranker (Optional):**
- Free API for reranking search results
- Improves relevance significantly
- Works with existing vector search
- Graceful fallback if unavailable

**Usage:**
```python
# With reranking (better results)
db.search_knowledge("AI research", limit=5, rerank=True)

# Without reranking (faster)
db.search_knowledge("AI research", limit=5, rerank=False)
```

### 4. Simplified Researcher

**Scaled down to basics:**
- Quick web search (DuckDuckGo)
- Check knowledge base first
- Short, concise answers
- No heavy multi-API calls

**When to use:**
- Quick lookups: "What's the weather?"
- Simple facts: "When was Python created?"
- Fast web search: "Latest SpaceX news"

**For deep content:**
Use content_saver instead - save the URLs, build your graph!

## How Content Flows Now

### Before (Heavy Research):
```
User Query → Multi-API Search → Query Analysis →
Tavily + DuckDuckGo + Brave → Synthesis → Cache → Response
(60-90 seconds, 10+ API calls)
```

### After (Content Curation):
```
User Shares URL → Extract Content → Generate Tags →
Save to Vector Store + Knowledge Graph → Auto-link → Response
(5-10 seconds, 1 extraction)
```

## Cost Comparison

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| Research API calls | Tavily ($0.001/search) + Brave | None | ~$0.01-0.05/query |
| Knowledge Graph | None | NetworkX (local) | $0 |
| Reranking | None | Jina (free tier) | $0 |
| Embeddings | OpenAI ($0.02/1M tokens) | Same | Same |
| **Per Query** | **$0.01-0.05** | **~$0** | **100% savings** |

## Embedding & Retrieval Strategy

### Current Setup:

**Embeddings:**
- Model: `text-embedding-3-small` (OpenAI)
- Cost: $0.02 per 1M tokens
- Quality: Good for general semantic search
- Speed: Fast

**Retrieval:**
1. ChromaDB vector search (cosine similarity)
2. Optional Jina reranking (improves top results)
3. Knowledge graph connections (find related notes)

**Is it contextual retrieval?**
Not yet, but easy to add:
- Contextual retrieval prepends context to chunks before embedding
- Improves accuracy by ~10-20%
- Adds ~20% to embedding cost
- Can implement if needed

**Do we use a reranker?**
Yes! Jina reranker (optional, free):
- Reranks top N results from vector search
- Significantly improves relevance
- Free tier: 1M tokens/month
- Falls back gracefully if unavailable

### Potential Upgrades:

| Upgrade | Cost | Benefit |
|---------|------|---------|
| Contextual Retrieval | +20% embedding cost | +10-20% accuracy |
| Voyage AI embeddings | $0.10/1M tokens | Better quality |
| Cohere reranker | $1/1K searches | Enterprise-grade |
| Local reranker | $0 (compute only) | Full control |

## Key Benefits

✅ **Zero ongoing costs** (uses local graph, free reranker)
✅ **Automatic connections** (Obsidian-style [[linking]])
✅ **Fast saves** (5-10 seconds vs 60-90 seconds)
✅ **True knowledge graph** (not just vector search)
✅ **Scalable** (NetworkX handles 100K+ nodes easily)
✅ **Simple** (no complex multi-API orchestration)
✅ **Better for PKM** (Personal Knowledge Management)

## Usage Examples

### Save an Article
```
You: https://paulgraham.com/greatwork.html

Bot: 💾 Extracting and organizing this content...
Bot: ✅ Content saved to knowledge graph!

Title: How to Do Great Work
Tags: career, creativity, advice, work, life
Size: 15,234 characters
🔗 Auto-linked to 3 related notes
```

### Save a Tweet Thread
```
You: https://twitter.com/elonmusk/status/123456789

Bot: 🐦 Detected Twitter/X URL
Bot: ✅ Content saved to knowledge graph!

Title: Tweet by @elonmusk
Tags: twitter, technology, saved-content
🔗 Auto-linked to 1 related note
```

### Save a Note
```
You: Remember: Spaced repetition is key to long-term memory retention

Bot: 📝 Saving as plain note
Bot: ✅ Content saved to knowledge graph!

Title: Memory Retention Note
Tags: memory, learning, study, retention
🔗 Auto-linked to 2 related notes
```

### Quick Search
```
You: Quick search for Python tutorials

Bot: 🔍 Researcher activated
Bot: Found in knowledge base:
1. Python for Beginners - Complete Guide...
2. Advanced Python Patterns...

Web search results:
1. Real Python - Python Tutorials
   Comprehensive Python tutorials for all levels...
```

## What's Next?

Future enhancements to consider:
1. **Graph visualization** - Visual map of your knowledge (like Obsidian graph view)
2. **Twitter API** - Full tweet thread extraction
3. **PDF support** - Save and extract from PDFs
4. **Smart suggestions** - "You might want to connect this to..."
5. **Export to Obsidian** - Sync your graph to actual Obsidian vault
6. **Advanced relationships** - Manually add custom edge types
7. **Graph queries** - "Show me all AI notes from last month"

## Technical Notes

**Knowledge Graph Storage:**
- Format: NetworkX MultiDiGraph (directed, multiple edges)
- Persistence: Pickle file at `data/knowledge_graph.pkl`
- Backup: Automatically saved after each change
- Size: ~1KB per node + metadata

**Node Attributes:**
```python
{
    'title': str,
    'content': str,
    'tags': List[str],
    'created_at': datetime,
    'type': 'webpage' | 'note',
    'url': Optional[str],
    'metadata': Dict
}
```

**Edge Attributes:**
```python
{
    'relationship': str,  # 'related-to', 'mentions', 'cites', etc.
    'reason': str,        # Why connected
    'created_at': datetime
}
```

## Files Changed

- `agents/content_saver.py` - New primary agent
- `agents/researcher.py` - Simplified (backup saved)
- `common/knowledge_graph.py` - Graph implementation
- `common/database.py` - Added reranking
- `main.py` - Updated routing and help
- `requirements.txt` - Added NetworkX

## Testing the New System

Try these commands in Telegram:

1. **Save content:**
   - Share any URL
   - "Remember: [your note]"

2. **Quick search:**
   - "Search for [topic]"
   - "What did I save about [topic]?"

3. **See connections:**
   - Save multiple notes with shared tags
   - Watch auto-linking happen

4. **Graph stats:**
   - Content saver will show connection counts
   - See how your knowledge grows

---

**Questions or feedback?** Let me know how the new system works for you!
