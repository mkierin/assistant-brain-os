import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from .config import DATABASE_PATH, CHROMA_PATH, OPENAI_API_KEY
from .contracts import KnowledgeEntry
import json
import os
import httpx
from typing import List, Dict, Optional

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

    def add_knowledge(self, entry: KnowledgeEntry):
        # Add to SQLite
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

        # Add to ChromaDB
        self.collection.add(
            documents=[entry.text],
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
