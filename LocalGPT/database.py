"""
LocalGPT: Database & Persistence Layer
Provides lightweight SQLite persistence for chat sessions, message histories,
and indexed document metadata.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class LocalGPTDatabase:
    """
    Manages local SQLite database operations for LocalGPT.
    Thread-safe and auto-creates schemas if they don't exist.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "localgpt.db")
        else:
            self.db_path = db_path
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Chat Sessions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model_name TEXT,
                system_prompt TEXT,
                total_tokens INTEGER DEFAULT 0
            )
            """)

            # 2. Messages
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                metadata_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )
            """)

            # 3. Documents
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """)

            # 4. Document Chunks
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
            )
            """)

            # Create Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(doc_id)")
            conn.commit()

    # ── Session Operations ───────────────────────────────────────────────────

    def create_session(self, session_id: str, title: str = "New Chat", model_name: str = "gpt2", system_prompt: str = "") -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, title, created_at, updated_at, model_name, system_prompt, total_tokens)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (session_id, title, now, now, model_name, system_prompt))
            conn.commit()

        return {
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "model_name": model_name,
            "system_prompt": system_prompt,
            "total_tokens": 0
        }

    def get_sessions(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_session_title(self, session_id: str, new_title: str):
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?", (new_title, now, session_id))
            conn.commit()

    def delete_session(self, session_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    # ── Message Operations ───────────────────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str, token_count: int = 0, metadata: Optional[Dict[str, Any]] = None) -> int:
        now = datetime.utcnow().isoformat()
        meta_str = json.dumps(metadata or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO messages (session_id, role, content, timestamp, token_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, role, content, now, token_count, meta_str))
            msg_id = cursor.lastrowid
            
            # Update session's updated_at and total token count
            cursor.execute("""
            UPDATE sessions 
            SET updated_at = ?, total_tokens = total_tokens + ? 
            WHERE session_id = ?
            """, (now, token_count, session_id))
            conn.commit()
            return msg_id

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
            rows = cursor.fetchall()
            messages = []
            for r in rows:
                d = dict(r)
                if d.get("metadata_json"):
                    try:
                        d["metadata"] = json.loads(d["metadata_json"])
                    except Exception:
                        d["metadata"] = {}
                messages.append(d)
            return messages

    def clear_session_messages(self, session_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("UPDATE sessions SET total_tokens = 0 WHERE session_id = ?", (session_id,))
            conn.commit()

    # ── Document Operations ──────────────────────────────────────────────────

    def register_document(self, doc_id: str, filename: str, file_type: str, file_path: str, file_size: int, chunk_count: int) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO documents (doc_id, filename, file_type, file_path, file_size, chunk_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, filename, file_type, file_path, file_size, chunk_count, now))
            conn.commit()
        return {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "file_path": file_path,
            "file_size": file_size,
            "chunk_count": chunk_count,
            "created_at": now
        }

    def list_documents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, doc_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
            cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Returns aggregate database metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as session_count FROM sessions")
            session_count = cursor.fetchone()["session_count"]

            cursor.execute("SELECT COUNT(*) as message_count FROM messages")
            message_count = cursor.fetchone()["message_count"]

            cursor.execute("SELECT COUNT(*) as doc_count FROM documents")
            doc_count = cursor.fetchone()["doc_count"]

            cursor.execute("SELECT COUNT(*) as chunk_count FROM document_chunks")
            chunk_count = cursor.fetchone()["chunk_count"]

            return {
                "total_sessions": session_count,
                "total_messages": message_count,
                "total_documents": doc_count,
                "total_chunks": chunk_count,
                "database_path": self.db_path
            }

    def get_message_count(self, session_id: str) -> int:
        """Returns the number of messages in a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def get_sessions_with_counts(self) -> List[Dict[str, Any]]:
        """Returns all sessions with message counts, ordered by most recently updated."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def rename_session(self, session_id: str, new_title: str):
        """Alias for update_session_title for semantic clarity."""
        self.update_session_title(session_id, new_title)

