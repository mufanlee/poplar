"""SQLite-based session and message persistence."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from poplar.core.session import Session, Message, Role
from poplar.utils import get_db_path


class SessionStore:
    """Manages SQLite persistence for sessions and messages."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new connection for thread-safe access."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Create tables if they don't exist, add new columns as needed."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            # Add new columns for existing databases
            for col in ['tool_calls', 'tool_call_id', 'name']:
                try:
                    conn.execute(f"ALTER TABLE messages ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            conn.commit()
        finally:
            conn.close()

    def create_session(self, session_id: Optional[str] = None, title: str = "New Chat") -> Session:
        """Create a new session and persist it."""
        session_id = session_id or uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now),
            )
            conn.commit()
        finally:
            conn.close()
        return Session(id=session_id, title=title)

    def get_session(self, session_id: str) -> Optional[Session]:
        """Load a session and its messages from the database."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return None

            session = Session(
                id=row[0],
                title=row[1],
                created_at=datetime.fromisoformat(row[2]),
            )

            msg_rows = conn.execute(
                "SELECT role, content, tool_calls, tool_call_id, name, created_at "
                "FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

            for msg_row in msg_rows:
                tool_calls = None
                if msg_row[2]:
                    try:
                        tool_calls = json.loads(msg_row[2])
                    except json.JSONDecodeError:
                        pass
                session.add_message(
                    Message(
                        role=Role(msg_row[0]),
                        content=msg_row[1] or "",
                        tool_calls=tool_calls,
                        tool_call_id=msg_row[3],
                        name=msg_row[4],
                    )
                )

            return session
        finally:
            conn.close()

    def list_sessions(self) -> List[Session]:
        """List all sessions ordered by last updated."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            sessions = []
            for row in rows:
                # Count messages for this session
                count = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                    (row[0],),
                ).fetchone()[0]
                
                session = Session(
                    id=row[0],
                    title=row[1],
                    created_at=datetime.fromisoformat(row[2]),
                )
                session._message_count = count  # type: ignore[attr-defined]
                sessions.append(session)
            return sessions
        finally:
            conn.close()

    def save_message(self, session_id: str, message: Message):
        """Persist a message to the database."""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            tool_calls_json = json.dumps(message.tool_calls) if message.tool_calls else None
            conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id, name, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, message.role.value, message.content or "",
                 tool_calls_json, message.tool_call_id, message.name, now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_session(self, session_id: str):
        """Delete a session and all its messages."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def update_title(self, session_id: str, title: str):
        """Update a session's title."""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_message_count(self, session_id: str) -> int:
        """Count meaningful (non-system) messages in a session."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role != 'system'",
                (session_id,),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
