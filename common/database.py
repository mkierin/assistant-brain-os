import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from .config import DATABASE_PATH, CHROMA_PATH, OPENAI_API_KEY
from .contracts import KnowledgeEntry
import json
import os

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

    def search_knowledge(self, query: str, limit: int = 5):
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        return results

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
