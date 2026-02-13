#!/usr/bin/env python3
"""
Re-index the knowledge base: fix IDs, enrich content, re-embed, deduplicate.

Run: cd /root/assistant-brain-os && source venv/bin/activate && python scripts/reindex_knowledge.py

What it does:
1. Reads all entries from SQLite (source of truth)
2. Fixes broken IDs (text[:50] -> proper UUIDs)
3. Enriches tweets and short content with LLM (extracts meaning)
4. Removes exact duplicates (by content hash)
5. Wipes and re-creates ChromaDB embeddings with improved contextual text
6. Chunks long documents for better semantic coverage
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import json
import uuid
import hashlib
import re
from common.database import db
from common.contracts import KnowledgeEntry


async def enrich_content(text: str, content_type: str) -> str:
    """Enrich short content (tweets, brief webpages) with expanded meaning."""
    # Only enrich short content that would benefit
    if len(text) > 800 or content_type not in ("tweet", "webpage"):
        return text

    # Strip the "# Title\n\n" prefix to get actual content for enrichment
    content_for_llm = text
    if text.startswith("# "):
        # Find end of title line
        newline_pos = text.find("\n")
        if newline_pos > 0:
            content_for_llm = text[newline_pos:].strip()

    try:
        from common.llm import get_async_client, get_model_name
        client = get_async_client()
        model = get_model_name()

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "You are a knowledge base assistant. Given a short piece of content (a tweet, brief post, etc.), "
                    "extract and expand its meaning into a concise knowledge note. Include:\n"
                    "- The core idea or claim being made\n"
                    "- Key entities, technologies, or concepts mentioned\n"
                    "- Any implicit context that would help find this later\n\n"
                    "Write 2-4 sentences. Be factual, don't add opinions. "
                    "Start with 'Key insight:' or 'About:'."
                )},
                {"role": "user", "content": f"Content ({content_type}):\n{content_for_llm}"}
            ],
            temperature=0.2,
            max_tokens=200
        )
        enrichment = response.choices[0].message.content.strip()
        # Prepend enrichment to original text
        return f"{enrichment}\n\n---\n\n{text}"
    except Exception as e:
        print(f"  Warning: enrichment failed: {e}")
        return text


async def main():
    print("=" * 60)
    print("Knowledge Base Re-indexer")
    print("=" * 60)

    # Step 1: Read all entries from SQLite
    db.cursor.execute(
        "SELECT id, text, tags, source, metadata, created_at FROM knowledge ORDER BY created_at"
    )
    rows = db.cursor.fetchall()
    print(f"\nFound {len(rows)} entries in SQLite")

    # Step 2: Detect and fix broken IDs, collect entries
    entries = []
    id_fixes = {}  # old_id -> new_id

    for row in rows:
        old_id, text, tags_json, source, meta_json, created_at = row
        tags = json.loads(tags_json) if tags_json else []
        metadata = json.loads(meta_json) if meta_json else {}
        content_type = metadata.get("content_type", "unknown")

        # Check if ID is a proper UUID
        try:
            uuid.UUID(old_id)
            new_id = old_id  # Already a UUID
        except ValueError:
            # Broken ID (text[:50] or hash) - generate a new UUID
            new_id = str(uuid.uuid4())
            id_fixes[old_id] = new_id
            print(f"  Fix ID: {old_id[:40]}... -> {new_id}")

        entries.append({
            "old_id": old_id,
            "new_id": new_id,
            "text": text or "",
            "tags": tags,
            "source": source or "",
            "metadata": metadata,
            "content_type": content_type,
            "created_at": created_at or "",
        })

    if id_fixes:
        print(f"\nFixing {len(id_fixes)} broken IDs in SQLite...")
        for old_id, new_id in id_fixes.items():
            db.cursor.execute("UPDATE knowledge SET id = ? WHERE id = ?", (new_id, old_id))
        db.conn.commit()
        print("  Done.")

    # Step 3: Deduplicate by content hash
    print(f"\nDeduplicating...")
    seen_hashes = {}
    unique_entries = []
    dupes_removed = 0

    for entry in entries:
        content_hash = hashlib.sha256(entry["text"].strip().lower().encode()).hexdigest()[:32]
        if content_hash in seen_hashes:
            # Duplicate - remove from SQLite
            print(f"  Removing duplicate: {entry['text'][:60]}...")
            db.cursor.execute("DELETE FROM knowledge WHERE id = ?", (entry["new_id"],))
            dupes_removed += 1
        else:
            seen_hashes[content_hash] = entry["new_id"]
            entry["content_hash"] = content_hash
            unique_entries.append(entry)

    if dupes_removed:
        db.conn.commit()
        print(f"  Removed {dupes_removed} duplicates.")
    else:
        print(f"  No duplicates found.")

    # Step 4: Enrich short content
    print(f"\nEnriching short content...")
    enriched_count = 0

    for entry in unique_entries:
        text = entry["text"]
        content_type = entry["content_type"]

        # Only enrich tweets and short webpages
        if content_type in ("tweet", "webpage") and len(text) < 800:
            print(f"  Enriching [{content_type}]: {text[:60]}...")
            enriched = await enrich_content(text, content_type)
            if enriched != text:
                entry["text"] = enriched
                # Update SQLite with enriched text
                db.cursor.execute(
                    "UPDATE knowledge SET text = ? WHERE id = ?",
                    (enriched, entry["new_id"])
                )
                enriched_count += 1

    if enriched_count:
        db.conn.commit()
        print(f"  Enriched {enriched_count} entries.")

    # Step 5: Update metadata with content_hash
    print(f"\nUpdating metadata...")
    for entry in unique_entries:
        meta = entry["metadata"]
        meta["content_hash"] = entry["content_hash"]
        db.cursor.execute(
            "UPDATE knowledge SET metadata = ? WHERE id = ?",
            (json.dumps(meta), entry["new_id"])
        )
    db.conn.commit()

    # Step 6: Wipe ChromaDB and re-embed everything
    print(f"\nWiping ChromaDB ({db.collection.count()} entries)...")
    # Delete all existing entries
    existing = db.collection.get()
    if existing["ids"]:
        db.collection.delete(ids=existing["ids"])
    print(f"  Cleared. ChromaDB now has {db.collection.count()} entries.")

    print(f"\nRe-embedding {len(unique_entries)} entries...")
    for i, entry in enumerate(unique_entries):
        ke = KnowledgeEntry(
            text=entry["text"],
            tags=entry["tags"],
            source=entry["source"],
            metadata=entry["metadata"],
            created_at=entry["created_at"],
        )

        # Chunk text for better semantic coverage
        chunks = db._chunk_text(entry["text"])

        if len(chunks) == 1:
            # Short text: single embedding with contextual prefix
            text_to_embed = db._create_contextual_text(ke)
            db.collection.add(
                documents=[text_to_embed],
                metadatas=[{**entry["metadata"], "source": entry["source"], "tags": ",".join(entry["tags"])}],
                ids=[entry["new_id"]]
            )
        else:
            # Long text: multiple chunk embeddings
            chunk_docs = []
            chunk_metas = []
            chunk_ids = []
            for ci, chunk in enumerate(chunks):
                chunk_ke = KnowledgeEntry(
                    text=chunk, tags=entry["tags"], source=entry["source"],
                    metadata=entry["metadata"], created_at=entry["created_at"]
                )
                chunk_docs.append(db._create_contextual_text(chunk_ke))
                chunk_metas.append({
                    **entry["metadata"],
                    "source": entry["source"],
                    "tags": ",".join(entry["tags"]),
                    "chunk_index": ci,
                    "parent_id": entry["new_id"],
                })
                chunk_ids.append(f"{entry['new_id']}_chunk_{ci}")

            db.collection.add(
                documents=chunk_docs,
                metadatas=chunk_metas,
                ids=chunk_ids
            )

        ct = entry["content_type"]
        chunks_str = f" ({len(chunks)} chunks)" if len(chunks) > 1 else ""
        print(f"  [{i+1}/{len(unique_entries)}] {ct:10s} | {len(entry['text']):5d} chars{chunks_str} | {entry['text'][:50]}...")

    # Step 7: Verify
    print(f"\n{'=' * 60}")
    print(f"RESULTS:")
    print(f"  SQLite entries: {db.get_all_entries_count()}")
    print(f"  ChromaDB entries: {db.collection.count()}")
    print(f"  IDs fixed: {len(id_fixes)}")
    print(f"  Duplicates removed: {dupes_removed}")
    print(f"  Content enriched: {enriched_count}")
    print(f"{'=' * 60}")

    # Quick test: search for something
    print(f"\nTest search: 'hugging face'")
    results = db.search_clean("hugging face", limit=3)
    for r in results:
        print(f"  - {r['title']}: {r['content'][:100]}...")

    print(f"\nDone! Your knowledge base has been re-indexed.")


if __name__ == "__main__":
    asyncio.run(main())
