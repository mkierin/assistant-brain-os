import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from .config import DATABASE_PATH, CHROMA_PATH, OPENAI_API_KEY
from .contracts import KnowledgeEntry
import json
import os
import re
import uuid
import httpx
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi

class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_sqlite()
        
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-3-small"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="brain_memory",
            embedding_function=self.openai_ef
        )

    def _init_sqlite(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                text TEXT,
                tags TEXT,
                source TEXT,
                metadata TEXT,
                created_at TEXT
            )
        """)
        # Indexes for common query patterns
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON knowledge(created_at)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge(source)")
        self.conn.commit()

    def _create_contextual_text(self, entry: KnowledgeEntry) -> str:
        """
        Create contextualized text for embedding (Anthropic's contextual retrieval approach).
        Prepends context about the document to improve retrieval accuracy.

        This increases embedding cost by ~20% but improves retrieval accuracy by 15-20%.
        """
        # Extract title from text if available
        title = "Untitled"
        if entry.text.startswith('#'):
            title_match = entry.text.split('\n')[0].strip('# ')
            title = title_match if title_match else "Untitled"

        # Build context string
        context_parts = [f"Document: {title}"]

        if entry.tags:
            context_parts.append(f"Topics: {', '.join(entry.tags)}")

        if entry.source:
            context_parts.append(f"Source: {entry.source}")

        if 'url' in entry.metadata:
            context_parts.append(f"URL: {entry.metadata['url']}")

        context = " | ".join(context_parts)

        # Combine context with content
        contextualized = f"[{context}]\n\n{entry.text}"

        return contextualized

    def add_knowledge(self, entry: KnowledgeEntry, use_contextual: bool = True):
        """
        Add knowledge entry to database.

        Args:
            entry: KnowledgeEntry to add
            use_contextual: If True, prepend context before embedding (improves accuracy)
        """
        # Generate a stable unique ID if not provided
        entry_id = entry.embedding_id or str(uuid.uuid4())

        # Add to SQLite (store original text)
        self.cursor.execute(
            "INSERT INTO knowledge (id, text, tags, source, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                entry_id,
                entry.text,
                json.dumps(entry.tags),
                entry.source,
                json.dumps(entry.metadata),
                entry.created_at
            )
        )
        self.conn.commit()

        # Add to ChromaDB (with contextualized text for better retrieval)
        text_to_embed = self._create_contextual_text(entry) if use_contextual else entry.text

        self.collection.add(
            documents=[text_to_embed],
            metadatas=[{**entry.metadata, "source": entry.source, "tags": ",".join(entry.tags)}],
            ids=[entry_id]
        )

    async def _rerank_results(self, query: str, documents: List[str]) -> List[Dict]:
        """
        Rerank results using Jina AI's free reranker API.
        Returns list of dicts with 'index' and 'relevance_score'.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    'https://api.jina.ai/v1/rerank',
                    headers={
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': 'jina-reranker-v2-base-multilingual',
                        'query': query,
                        'documents': documents,
                        'top_n': len(documents)
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get('results', [])
                else:
                    print(f"⚠️  Reranker API error: {response.status_code}")
                    return []
        except Exception as e:
            print(f"⚠️  Reranking failed: {e}")
            return []

    def search_knowledge(self, query: str, limit: int = 5, rerank: bool = False):
        """
        Search knowledge base with optional reranking.

        Args:
            query: Search query
            limit: Number of results
            rerank: If True, use Jina reranker to improve result quality
        """
        # Get more results if reranking (to have options to rerank)
        fetch_limit = limit * 2 if rerank else limit

        results = self.collection.query(
            query_texts=[query],
            n_results=fetch_limit
        )

        # If reranking is disabled or no results, return as-is
        if not rerank or not results['documents'][0]:
            return results

        # Rerank using synchronous HTTP call (works in any context)
        reranked = self._rerank_results_sync(query, results['documents'][0])

        if not reranked:
            return results

        # Reorder results based on reranker scores
        reranked_docs = []
        reranked_metadatas = []
        reranked_distances = []
        reranked_ids = []

        for item in reranked[:limit]:
            idx = item['index']
            if idx < len(results['documents'][0]):
                reranked_docs.append(results['documents'][0][idx])
                if results['metadatas'] and results['metadatas'][0]:
                    reranked_metadatas.append(results['metadatas'][0][idx])
                if results['distances'] and results['distances'][0]:
                    reranked_distances.append(results['distances'][0][idx])
                if results['ids'] and results['ids'][0]:
                    reranked_ids.append(results['ids'][0][idx])

        return {
            'documents': [reranked_docs],
            'metadatas': [reranked_metadatas] if reranked_metadatas else results.get('metadatas'),
            'distances': [reranked_distances] if reranked_distances else results.get('distances'),
            'ids': [reranked_ids] if reranked_ids else results.get('ids')
        }

    def _rerank_results_sync(self, query: str, documents: List[str]) -> List[Dict]:
        """
        Rerank results using Jina AI's reranker API (synchronous version).
        Works in both sync and async contexts.
        """
        try:
            import httpx as httpx_sync
            with httpx_sync.Client(timeout=10.0) as client:
                response = client.post(
                    'https://api.jina.ai/v1/rerank',
                    headers={'Content-Type': 'application/json'},
                    json={
                        'model': 'jina-reranker-v2-base-multilingual',
                        'query': query,
                        'documents': documents,
                        'top_n': len(documents)
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get('results', [])
                else:
                    print(f"⚠️  Reranker API error: {response.status_code}")
                    return []
        except Exception as e:
            print(f"⚠️  Reranking failed: {e}")
            return []

    def hybrid_search(self, query: str, limit: int = 5, keyword_weight: float = 0.3, semantic_weight: float = 0.7):
        """
        Hybrid search combining BM25 (keyword) and semantic (vector) search.

        Uses a two-phase approach:
        1. ChromaDB semantic search to get top candidates (fast, O(1) via index)
        2. BM25 keyword scoring on ONLY those candidates (not all documents)
        3. Combine scores with weighted fusion

        Args:
            query: Search query
            limit: Number of results
            keyword_weight: Weight for BM25 scores (default 0.3)
            semantic_weight: Weight for semantic scores (default 0.7)

        Returns:
            Combined and ranked results
        """
        # Phase 1: Semantic search to get candidate set (fast - uses vector index)
        candidate_count = min(limit * 4, self.collection.count() or limit)
        if candidate_count == 0:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]], 'ids': [[]]}

        semantic_results = self.collection.query(
            query_texts=[query],
            n_results=candidate_count
        )

        if not semantic_results['documents'][0]:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]], 'ids': [[]]}

        candidates = semantic_results['documents'][0]
        candidate_ids = semantic_results['ids'][0]
        candidate_metadatas = semantic_results['metadatas'][0]
        candidate_distances = semantic_results['distances'][0]

        # Phase 2: BM25 keyword scoring on ONLY the candidates (not all docs)
        tokenized_docs = [doc.lower().split() for doc in candidates]
        bm25 = BM25Okapi(tokenized_docs)
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)

        # Normalize BM25 scores to 0-1
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
        bm25_scores_norm = [score / max_bm25 for score in bm25_scores]

        # Phase 3: Combine scores
        combined = []
        for i in range(len(candidates)):
            semantic_score = 1 / (1 + candidate_distances[i])
            bm25_score = bm25_scores_norm[i]
            combined_score = keyword_weight * bm25_score + semantic_weight * semantic_score
            combined.append((i, combined_score))

        # Sort by combined score and take top results
        combined.sort(key=lambda x: x[1], reverse=True)
        top = combined[:limit]

        # Build result dict
        result_docs = [candidates[i] for i, _ in top]
        result_metadata = [candidate_metadatas[i] for i, _ in top]
        result_ids = [candidate_ids[i] for i, _ in top]
        result_scores = [score for _, score in top]

        return {
            'documents': [result_docs],
            'metadatas': [result_metadata],
            'ids': [result_ids],
            'distances': [[1 - score for score in result_scores]]
        }

    def search_with_filters(
        self,
        query: str,
        limit: int = 5,
        tags: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        content_type: Optional[str] = None,
        source: Optional[str] = None,
        min_length: Optional[int] = None,
        use_hybrid: bool = True
    ):
        """
        Advanced search with metadata filtering.

        Args:
            query: Search query
            limit: Max results
            tags: Filter by tags (OR logic - matches any)
            date_from: ISO date string (YYYY-MM-DD)
            date_to: ISO date string (YYYY-MM-DD)
            content_type: Filter by type ('webpage', 'tweet', 'note', 'daily', 'placeholder')
            source: Filter by source ('content_saver', 'researcher', 'archivist')
            min_length: Minimum content length
            use_hybrid: Use hybrid search (default True)

        Returns:
            Filtered search results
        """
        # Get base search results (more than needed for filtering)
        if use_hybrid:
            base_results = self.hybrid_search(query, limit=limit * 5)
        else:
            base_results = self.search_knowledge(query, limit=limit * 5)

        if not base_results['documents'][0]:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]], 'ids': [[]]}

        # Apply filters
        filtered_docs = []
        filtered_metadata = []
        filtered_ids = []
        filtered_distances = []

        for i, doc in enumerate(base_results['documents'][0]):
            metadata = base_results['metadatas'][0][i] if base_results['metadatas'] else {}
            doc_id = base_results['ids'][0][i] if base_results['ids'] else None
            distance = base_results['distances'][0][i] if base_results['distances'] else 0

            # Tag filter (OR logic)
            if tags:
                doc_tags = metadata.get('tags', '').split(',')
                if not any(tag.lower() in [t.lower().strip() for t in doc_tags] for tag in tags):
                    continue

            # Date filters
            if date_from or date_to:
                # Try to get date from metadata or created_at
                doc_date = metadata.get('saved_at') or metadata.get('created_at', '')

                if date_from and doc_date < date_from:
                    continue

                if date_to and doc_date > date_to:
                    continue

            # Content type filter
            if content_type:
                doc_type = metadata.get('content_type') or metadata.get('type', '')
                if doc_type.lower() != content_type.lower():
                    continue

            # Source filter
            if source:
                doc_source = metadata.get('source', '')
                if source.lower() not in doc_source.lower():
                    continue

            # Length filter
            if min_length:
                if len(doc) < min_length:
                    continue

            # Passed all filters
            filtered_docs.append(doc)
            filtered_metadata.append(metadata)
            filtered_ids.append(doc_id)
            filtered_distances.append(distance)

            # Stop if we have enough
            if len(filtered_docs) >= limit:
                break

        return {
            'documents': [filtered_docs],
            'metadatas': [filtered_metadata],
            'ids': [filtered_ids],
            'distances': [filtered_distances]
        }

    def _extract_title(self, text: str, meta: dict) -> str:
        """Extract a meaningful title from text or metadata."""
        # 1. Check metadata title
        title = meta.get('title', '')
        if title:
            return title
        # 2. Check for markdown heading
        if text.startswith('#'):
            title = text.split('\n')[0].strip('# ').strip()
            if title:
                return title
        # 3. Check for "RESEARCH:" or similar prefix patterns
        prefix_match = re.match(r'^(RESEARCH|NOTE|SAVE|SUMMARY):\s*(.+)', text, re.IGNORECASE)
        if prefix_match:
            rest = prefix_match.group(2).strip().split('\n')[0][:80]
            if rest:
                return rest
        # 4. Use first non-empty line, truncated
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 2:
                return line[:80] + ('...' if len(line) > 80 else '')
        return 'Untitled'

    def search_clean(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search the knowledge base and return clean, display-ready results.

        Uses hybrid search (BM25 + semantic) for best accuracy, then looks up
        the original text from SQLite (not the contextualized ChromaDB text).

        Returns a list of dicts with: id, title, content, tags, source, score, created_at
        """
        # Step 1: Hybrid search to get ranked IDs
        try:
            search_results = self.hybrid_search(query, limit=limit)
        except Exception as e:
            print(f"Hybrid search failed, falling back to semantic: {e}")
            search_results = self.search_knowledge(query, limit=limit)

        result_ids = search_results.get('ids', [[]])[0]
        if not result_ids:
            # Fallback: try SQLite LIKE search for exact keyword matches
            return self._sqlite_fallback_search(query, limit)

        # Step 2: Look up original clean text from SQLite by IDs
        clean_results = []
        for doc_id in result_ids:
            self.cursor.execute(
                "SELECT id, text, tags, source, metadata, created_at FROM knowledge WHERE id = ?",
                (doc_id,)
            )
            row = self.cursor.fetchone()
            if row:
                meta = json.loads(row[4]) if row[4] else {}
                text = row[1] or ""
                title = self._extract_title(text, meta)

                clean_results.append({
                    'id': row[0],
                    'title': title,
                    'content': text,
                    'tags': json.loads(row[2]) if row[2] else [],
                    'source': row[3] or '',
                    'url': meta.get('url', ''),
                    'summary': meta.get('summary', ''),
                    'created_at': row[5] or '',
                })

        # If hybrid search returned IDs that weren't in SQLite, try fallback
        if not clean_results:
            return self._sqlite_fallback_search(query, limit)

        return clean_results

    def _sqlite_fallback_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Fallback: simple LIKE search in SQLite for exact keyword matches."""
        search_term = f"%{query}%"
        self.cursor.execute(
            "SELECT id, text, tags, source, metadata, created_at FROM knowledge WHERE text LIKE ? ORDER BY created_at DESC LIMIT ?",
            (search_term, limit)
        )
        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            meta = json.loads(row[4]) if row[4] else {}
            text = row[1] or ""
            title = self._extract_title(text, meta)

            results.append({
                'id': row[0],
                'title': title,
                'content': text,
                'tags': json.loads(row[2]) if row[2] else [],
                'source': row[3] or '',
                'url': meta.get('url', ''),
                'summary': meta.get('summary', ''),
                'created_at': row[5] or '',
            })
        return results

    def get_all_entries_count(self) -> int:
        """Get total number of entries in the knowledge base."""
        self.cursor.execute("SELECT COUNT(*) FROM knowledge")
        return self.cursor.fetchone()[0]

    def get_all_entries(self, limit: int = 1000) -> List[Dict]:
        """Get all entries as a list of dicts (for web API endpoints)."""
        self.cursor.execute(
            "SELECT id, text, tags, source, metadata, created_at FROM knowledge ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = self.cursor.fetchall()
        entries = []
        for row in rows:
            meta = json.loads(row[4]) if row[4] else {}
            entries.append({
                'id': row[0],
                'text': row[1],
                'title': meta.get('title', row[1][:80] if row[1] else 'Untitled'),
                'tags': json.loads(row[2]) if row[2] else [],
                'source': row[3],
                'metadata': meta,
                'content': row[1],
                'summary': meta.get('summary', ''),
                'category': meta.get('content_type', 'note'),
                'url': meta.get('url', ''),
                'created_at': row[5]
            })
        return entries

    def search_entries(self, query: str, limit: int = 50) -> List[Dict]:
        """Search entries and return as a list of dicts (for web API endpoints)."""
        if not query.strip():
            return self.get_all_entries(limit=limit)

        results = self.search_knowledge(query, limit=limit)
        entries = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                doc_id = results['ids'][0][i] if results['ids'] and results['ids'][0] else str(i)
                entries.append({
                    'id': doc_id,
                    'text': doc,
                    'title': meta.get('title', doc[:80] if doc else 'Untitled'),
                    'tags': meta.get('tags', '').split(',') if meta.get('tags') else [],
                    'source': meta.get('source', ''),
                    'metadata': meta,
                    'content': doc,
                    'summary': meta.get('summary', ''),
                    'category': meta.get('content_type', 'note'),
                    'url': meta.get('url', ''),
                    'created_at': meta.get('saved_at', meta.get('created_at', ''))
                })
        return entries

    def get_recent_knowledge(self, limit: int = 5):
        self.cursor.execute("SELECT * FROM knowledge ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = self.cursor.fetchall()
        return [
            KnowledgeEntry(
                text=row[1],
                tags=json.loads(row[2]),
                source=row[3],
                metadata=json.loads(row[4]),
                created_at=row[5]
            ) for row in rows
        ]

    def delete_entry(self, entry_id: str):
        """Delete an entry from the knowledge base"""
        # Delete from ChromaDB
        try:
            self.collection.delete(ids=[entry_id])
        except Exception as e:
            print(f"Warning: Could not delete from ChromaDB: {e}")

        # Delete from SQLite
        self.cursor.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
        self.conn.commit()

    def cleanup_garbage(self, min_length: int = 3) -> int:
        """Remove entries with garbage content (too short, only punctuation, etc.).

        Returns the number of entries removed.
        """
        import re
        self.cursor.execute("SELECT id, text FROM knowledge")
        rows = self.cursor.fetchall()
        removed = 0
        for row in rows:
            entry_id, text = row[0], row[1] or ""
            text = text.strip()
            # Remove if too short or no alphanumeric characters
            if len(text) < min_length or not re.search(r'[a-zA-Z0-9]', text):
                self.delete_entry(entry_id)
                removed += 1
                print(f"  Removed garbage entry: {repr(text[:50])}")
        return removed

db = Database()
