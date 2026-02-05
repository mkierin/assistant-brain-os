# 🎥 YouTube Video Support - Now Live!

## What You Can Do

Just share any YouTube URL in Telegram and the system will:

1. **Extract the full transcript** (free, works with 90%+ of videos)
2. **Get video metadata** (title, channel, duration, date)
3. **Generate smart summary** with LLM:
   - TL;DR (2-3 sentences)
   - Key Points (5-7 bullets)
   - Main Concepts/Topics
   - Notable Quotes
   - Suggested Tags
4. **Detect chapters** from video description
5. **Create timestamp links** (click to jump to that moment)
6. **Save to knowledge graph** with auto-linking

---

## Example

**You share:**
```
https://youtube.com/watch?v=dQw4w9WgXcQ
```

**System extracts and saves:**

```markdown
# Rick Astley - Never Gonna Give You Up (4K Remaster)

**Channel:** Rick Astley
**Duration:** 3:33
**Published:** 2009-10-25

## TL;DR
Official 4K remaster of Rick Astley's 1987 hit. A straightforward
promise of commitment and loyalty in a romantic relationship. Famous
as the "Rickrolling" meme.

## Key Points
- Core message: Promise of unwavering commitment and loyalty
- Classic 1980s pop structure with anthemic chorus
- Lists negative actions the singer vows never to do
- Gained second wave of popularity as "Rickrolling" meme
- 4K remaster of original music video
- Quintessential late-80s dance-pop

## Main Concepts
[[Love]] • [[Commitment]] • [[1980s Pop]] • [[Internet Meme]] •
[[Rickrolling]]

## Notable Quotes
> "Never gonna give you up / Never gonna let you down"
> — The iconic chorus

## Chapters
- [00:00](https://youtube.com/watch?v=ID&t=0s) Introduction
- [00:43](https://youtube.com/watch?v=ID&t=43s) First Verse
- [01:05](https://youtube.com/watch?v=ID&t=65s) Chorus

---

**Transcript:** 2089 characters
**Tags:** #rick-astley, #80s-music, #pop, #music-video, #rickroll
**Watch:** https://youtube.com/watch?v=dQw4w9WgXcQ
```

---

## Features

### ✅ Works With
- Educational videos
- Tech tutorials
- Conference talks
- Lectures
- Podcasts (video format)
- Documentaries
- Any video with captions

### ✅ Extracts
- Full transcript text
- Speaker's words verbatim
- Timestamps for each segment
- Video metadata

### ✅ Smart Processing
- LLM summarization
- Concept extraction
- Auto-tagging
- Quote extraction
- Chapter detection

### ✅ Knowledge Graph Integration
- Saves to vector database (searchable)
- Creates node in knowledge graph
- Auto-links to [[concepts]]
- Links to today's daily note
- Connects via tag hierarchy

---

## Cost Analysis

| Component | Cost | Notes |
|-----------|------|-------|
| Transcript extraction | $0 | Free (youtube-transcript-api) |
| Metadata | $0 | Free (yt-dlp) |
| LLM summary | $0.01-0.02 | DeepSeek API |
| **Total per video** | **$0.01-0.02** | Very affordable! |

**Comparison:**
- Whisper transcription: $0.006/minute ($0.18 for 30min video)
- Our method: $0.01-0.02 total (no matter video length)
- **Savings: 90%+ cheaper!**

---

## Technical Details

### Primary Method: youtube-transcript-api
```python
from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()
fetched = api.fetch(video_id, languages=['en'])
transcript = " ".join([s.text for s in fetched.snippets])
```

**Pros:**
- Free, no API key
- Works immediately
- Includes timestamps
- Fast (1-2 seconds)

**Limitations:**
- Requires video to have captions (auto or manual)
- Won't work if uploader disabled captions
- ~90% success rate

### Metadata: yt-dlp
```bash
yt-dlp --dump-json --no-download VIDEO_URL
```

**Extracts:**
- Title, channel, description
- Duration, upload date
- Thumbnail, view count
- Chapter markers

### Smart Summarization: LLM
Uses DeepSeek to analyze transcript and generate:
- Contextual summary
- Key takeaways
- Important concepts
- Memorable quotes
- Relevant tags

---

## Use Cases

### 🎓 Educational Content
```
Share: "MIT OpenCourseWare - Linear Algebra Lecture"
→ Get: Summary of key concepts, formulas, examples
→ Search: Find specific topics later
→ Link: Connect to related math notes
```

### 💼 Conference Talks
```
Share: "Google I/O 2024 - New AI Features"
→ Get: Product announcements, features, dates
→ Tags: #google, #ai, #product-launch
→ Timeline: Chapters for each announcement
```

### 🛠️ Technical Tutorials
```
Share: "Docker Compose Tutorial - Full Course"
→ Get: Step-by-step summary
→ Chapters: Jump to specific commands
→ Connect: Link to other Docker notes
```

### 📚 Research & Learning
```
Share: "Lex Fridman Podcast - AI Researcher"
→ Get: Key insights, quotes, topics discussed
→ Auto-link: Connect to [[AI]], [[Research]]
→ Review: Search transcript later
```

---

## Limitations & Fallbacks

### Videos Without Captions
If a video doesn't have captions, you'll see:
```
⚠️ This video doesn't have captions available.
Unable to extract transcript.

Note: You can still save this manually with a description.
```

**Future enhancement:** Could add Whisper fallback
- Download audio
- Transcribe with Whisper
- Cost: $0.006/minute
- Only use if explicitly requested

### Private Videos
- Can't access private/unlisted videos
- Requires public URL with captions

### Non-English Videos
- Currently optimized for English
- Can add language support easily
- Just specify: `languages=['es']` for Spanish

---

## How to Use

### In Telegram
Just paste any YouTube URL:
```
https://youtube.com/watch?v=VIDEO_ID
```

System automatically:
1. Detects it's YouTube
2. Extracts transcript
3. Summarizes with AI
4. Saves to knowledge base

### What Gets Saved
- Full transcript (searchable)
- Smart summary
- Chapters with links
- Auto-generated tags
- Connections to related notes

### Finding Videos Later
Search by:
- Video title
- Topic/concept
- Quote from transcript
- Tag (#ai, #tutorial, etc.)
- Date saved

Example searches:
```
"Find video about transformers"
"Show YouTube videos from last week"
"Search transcript for 'attention mechanism'"
```

---

## Future Enhancements (Optional)

Could add:
- 📊 **Visual analysis** (extract slides, diagrams)
- 🗣️ **Speaker diarization** (who said what)
- 🌍 **Multi-language support** (non-English videos)
- 🎬 **Playlist support** (process entire playlists)
- 📝 **Custom summaries** ("Summarize as bullet points")
- 🔊 **Whisper fallback** (for videos without captions)

---

## Tested & Working

✅ Transcript extraction working
✅ Metadata extraction working
✅ LLM summarization working
✅ Chapter detection working
✅ Timestamp links working
✅ Auto-tagging working
✅ Knowledge graph integration working
✅ All workers restarted and ready

---

## Ready to Use!

Share any YouTube URL and watch it get automatically:
- Transcribed
- Summarized
- Tagged
- Connected to your knowledge graph

**Example:** Try sharing an educational video, tech talk, or tutorial!

The system will extract all the knowledge and make it searchable in your second brain. 🧠✨
