"""
Semantic Cache with similarity matching for faster responses
"""

import sqlite3
import json
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
from langchain_openai import OpenAIEmbeddings

# Register datetime adapter for Python 3.12+ compatibility
sqlite3.register_adapter(datetime, lambda val: val.isoformat())
sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode()))
from src.config import OPENAI_API_KEY
from src.utils import logger


class SemanticCache:

    def __init__(
        self,
        db_path: str = "data/semantic_cache.db",
        similarity_threshold: float = 0.88,  # OPTIMIZED: Was 0.92, reduced for higher hit rate
        ttl_hours: int = 24,  # Cache expires after 24 hours
        max_entries: int = 1000
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self.max_entries = max_entries

        # Embeddings for semantic similarity
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",  # Fast & cheap
            api_key=OPENAI_API_KEY
        )

        # Initialize database
        self._init_db()

        # Stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }

        logger.info(f"SemanticCache initialized")
        logger.info(f"   - Similarity threshold: {similarity_threshold}")
        logger.info(f"   - TTL: {ttl_hours}h")
        logger.info(f"   - Max entries: {max_entries}")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                query_embedding BLOB NOT NULL,
                answer TEXT NOT NULL,
                metadata TEXT,
                system_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP
            )
        """)

        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
        """)

        conn.commit()
        conn.close()

        logger.info("Cache database initialized")

    def _embedding_to_blob(self, embedding: List[float]) -> bytes:
        return np.array(embedding, dtype=np.float32).tobytes()

    def _blob_to_embedding(self, blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32)

    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

    def _cleanup_expired(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM cache WHERE expires_at < ?
        """, (datetime.now(),))

        deleted = cursor.rowcount
        if deleted > 0:
            logger.debug(f"[Cache] Cleaned up {deleted} expired entries")

        conn.commit()
        conn.close()

    def _enforce_max_entries(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count entries
        cursor.execute("SELECT COUNT(*) FROM cache")
        count = cursor.fetchone()[0]

        if count > self.max_entries:
            # Delete oldest accessed entries
            to_delete = count - self.max_entries
            cursor.execute("""
                DELETE FROM cache WHERE id IN (
                    SELECT id FROM cache
                    ORDER BY last_accessed ASC
                    LIMIT ?
                )
            """, (to_delete,))

            self.stats['evictions'] += cursor.rowcount
            logger.debug(f"[Cache] Evicted {cursor.rowcount} LRU entries")

        conn.commit()
        conn.close()

    async def get(
        self,
        query: str,
        system_type: str = "react_agent"
    ) -> Optional[Dict[str, Any]]:
        start = time.time()

        # Cleanup expired entries periodically
        self._cleanup_expired()

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        query_emb_array = np.array(query_embedding, dtype=np.float32)

        # Fetch all cache entries for this system type
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, query, query_embedding, answer, metadata, access_count
            FROM cache
            WHERE system_type = ? AND expires_at > ?
            ORDER BY last_accessed DESC
            LIMIT 100
        """, (system_type, datetime.now()))

        entries = cursor.fetchall()

        if not entries:
            conn.close()
            self.stats['misses'] += 1
            logger.debug(f"[Cache] MISS - No cached entries for {system_type}")
            return None

        # Find best matching entry
        best_match = None
        best_similarity = 0.0

        for entry in entries:
            entry_id, cached_query, cached_emb_blob, answer, metadata, access_count = entry

            # Calculate similarity
            cached_emb_array = self._blob_to_embedding(cached_emb_blob)
            similarity = self._cosine_similarity(query_emb_array, cached_emb_array)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    'id': entry_id,
                    'cached_query': cached_query,
                    'answer': answer,
                    'metadata': json.loads(metadata) if metadata else {},
                    'similarity': similarity,
                    'access_count': access_count
                }

        # Check if best match exceeds threshold
        if best_match and best_similarity >= self.similarity_threshold:
            # Update access stats
            cursor.execute("""
                UPDATE cache
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now(), best_match['id']))
            conn.commit()

            self.stats['hits'] += 1
            elapsed = (time.time() - start) * 1000

            logger.info(f"[Cache] HIT (similarity: {best_similarity:.3f}, {elapsed:.0f}ms)")
            logger.info(f"   Query: {query[:50]}...")
            logger.info(f"   Cached: {best_match['cached_query'][:50]}...")

            conn.close()
            return best_match

        conn.close()
        self.stats['misses'] += 1

        if best_match:
            logger.debug(f"[Cache] MISS - Best similarity {best_similarity:.3f} < {self.similarity_threshold}")

        return None

    async def set(
        self,
        query: str,
        answer: str,
        system_type: str = "react_agent",
        metadata: Optional[Dict] = None
    ):
        start = time.time()

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        query_emb_blob = self._embedding_to_blob(query_embedding)

        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)

        # Store in DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO cache (query, query_embedding, answer, metadata, system_type, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query,
            query_emb_blob,
            answer,
            json.dumps(metadata) if metadata else None,
            system_type,
            expires_at
        ))

        conn.commit()
        conn.close()

        # Enforce max entries
        self._enforce_max_entries()

        elapsed = (time.time() - start) * 1000
        logger.debug(f"[Cache] Stored entry ({elapsed:.0f}ms, expires in {self.ttl_hours}h)")

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count entries
        cursor.execute("SELECT COUNT(*) FROM cache WHERE expires_at > ?", (datetime.now(),))
        active_entries = cursor.fetchone()[0]

        # Calculate hit rate
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0

        conn.close()

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f"{hit_rate:.1f}%",
            'active_entries': active_entries,
            'evictions': self.stats['evictions'],
            'similarity_threshold': self.similarity_threshold
        }

    def clear(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cache")
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"[Cache] Cleared {deleted} entries")

        # Reset stats
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}


# Global cache instance
_cache_instance = None

def get_cache() -> SemanticCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance
