import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from .config import DATABASE_PATH, CHROMA_PATH, OPENAI_API_KEY
from .contracts import KnowledgeEntry
import json
import os
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
        # Add to SQLite (store original text)
        self.cursor.execute(
            "INSERT INTO knowledge (id, text, tags, source, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                entry.embedding_id or entry.text[:50], # fallback ID
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
            ids=[entry.embedding_id or str(hash(entry.text))]
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

        # Rerank results synchronously using asyncio
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't use run()
                # Just return without reranking in this case
                return results
            else:
                reranked = loop.run_until_complete(
                    self._rerank_results(query, results['documents'][0])
                )
        except Exception:
            # Fallback: return without reranking
            return results

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

    def hybrid_search(self, query: str, limit: int = 5, keyword_weight: float = 0.3, semantic_weight: float = 0.7):
        """
        Hybrid search combining BM25 (keyword) and semantic (vector) search.

        Args:
            query: Search query
            limit: Number of results
            keyword_weight: Weight for BM25 scores (default 0.3)
            semantic_weight: Weight for semantic scores (default 0.7)

        Returns:
            Combined and ranked results
        """
        # Get all documents for BM25
        all_results = self.collection.get()

        if not all_results['documents']:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]], 'ids': [[]]}

        documents = all_results['documents']
        ids = all_results['ids']
        metadatas = all_results['metadatas']

        # 1. BM25 keyword search
        tokenized_docs = [doc.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)

        # Normalize BM25 scores to 0-1
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
        bm25_scores_norm = [score / max_bm25 for score in bm25_scores]

        # 2. Semantic vector search
        semantic_results = self.collection.query(
            query_texts=[query],
            n_results=min(len(documents), limit * 3)
        )

        # Create semantic score dict (use inverse distance as score)
        semantic_scores = {}
        if semantic_results['documents'][0]:
            for i, doc_id in enumerate(semantic_results['ids'][0]):
                # Convert distance to similarity score (lower distance = higher score)
                distance = semantic_results['distances'][0][i] if semantic_results['distances'] else 0
                semantic_scores[doc_id] = 1 / (1 + distance)

        # 3. Combine scores
        combined_scores = {}
        for i, doc_id in enumerate(ids):
            bm25_score = bm25_scores_norm[i]
            semantic_score = semantic_scores.get(doc_id, 0)

            # Weighted combination
            combined_scores[doc_id] = (
                keyword_weight * bm25_score +
                semantic_weight * semantic_score
            )

        # 4. Sort and get top results
        ranked_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:limit]

        # 5. Build result dict
        result_docs = []
        result_metadata = []
        result_ids = []
        result_scores = []

        for doc_id in ranked_ids:
            idx = ids.index(doc_id)
            result_docs.append(documents[idx])
            result_metadata.append(metadatas[idx])
            result_ids.append(doc_id)
            result_scores.append(combined_scores[doc_id])

        return {
            'documents': [result_docs],
            'metadatas': [result_metadata],
            'ids': [result_ids],
            'distances': [[1 - score for score in result_scores]]  # Convert back to distances
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

db = Database()
