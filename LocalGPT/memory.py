"""
LocalGPT: Memory & Context Window Manager
Provides multi-turn conversational memory, token budgeting, sliding window context trimming,
and session serialization.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import os

try:
    from .database import LocalGPTDatabase
except (ImportError, ValueError):
    from database import LocalGPTDatabase


@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            token_count=data.get("token_count", 0),
            metadata=data.get("metadata", {})
        )


class MemoryManager:
    """
    Manages conversational memory with configurable strategies:
    - 'buffer': keeps all messages
    - 'sliding_window': keeps the most recent N turns or fits within max_tokens
    """

    def __init__(
        self,
        session_id: str = "default_session",
        strategy: str = "sliding_window",
        max_turns: int = 10,
        max_context_tokens: int = 2048,
        db: Optional[LocalGPTDatabase] = None
    ):
        self.session_id = session_id
        self.strategy = strategy
        self.max_turns = max_turns
        self.max_context_tokens = max_context_tokens
        self.system_prompt = "You are LocalGPT, a helpful, precise, and privacy-preserving AI assistant."
        self.messages: List[ChatMessage] = []
        self.db = db or LocalGPTDatabase()
        self._load_from_db()

    def _load_from_db(self):
        """Loads messages from SQLite database if existing."""
        db_session = self.db.get_session(self.session_id)
        if db_session:
            if db_session.get("system_prompt"):
                self.system_prompt = db_session["system_prompt"]
            raw_msgs = self.db.get_messages(self.session_id)
            self.messages = [ChatMessage.from_dict(m) for m in raw_msgs]
        else:
            self.db.create_session(self.session_id, title="New Conversation", system_prompt=self.system_prompt)

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt.strip()
        self.db.create_session(self.session_id, system_prompt=self.system_prompt)

    def add_message(self, role: str, content: str, token_count: int = 0, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        msg = ChatMessage(
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.db.save_message(self.session_id, role, content, token_count, metadata)
        return msg

    def add_user_message(self, content: str, token_count: int = 0, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        return self.add_message("user", content, token_count, metadata)

    def add_assistant_message(self, content: str, token_count: int = 0, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        return self.add_message("assistant", content, token_count, metadata)

    def get_history(self) -> List[ChatMessage]:
        return list(self.messages)

    def get_formatted_messages_for_llm(self) -> List[Dict[str, str]]:
        """
        Formats messages for LLM consumption, applying sliding window context pruning
        while ensuring the system prompt remains at the top.
        """
        formatted = [{"role": "system", "content": self.system_prompt}]

        if self.strategy == "sliding_window":
            # Keep the last max_turns user-assistant pairs (2 * max_turns)
            window = self.messages[-(self.max_turns * 2):]
        else:
            window = self.messages

        for m in window:
            formatted.append({"role": m.role, "content": m.content})

        return formatted

    def get_flat_prompt(self) -> str:
        """
        Constructs a plain-text multi-turn prompt suitable for models without native chat templates.
        """
        lines = [f"System: {self.system_prompt}"]
        for m in self.get_formatted_messages_for_llm()[1:]:
            role_label = "User" if m["role"] == "user" else "Assistant"
            lines.append(f"{role_label}: {m['content']}")
        lines.append("Assistant:")
        return "\n\n".join(lines)

    def pop_last_assistant(self):
        """Removes the last assistant message from in-memory history and the database."""
        # Remove from in-memory list
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].role == "assistant":
                self.messages.pop(i)
                break

        # Remove the last assistant row from DB
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages WHERE id = (
                    SELECT id FROM messages
                    WHERE session_id = ? AND role = 'assistant'
                    ORDER BY id DESC LIMIT 1
                )
            """, (self.session_id,))
            conn.commit()

    def truncate_after(self, keep_up_to_index: int):
        """
        Removes all messages at index >= keep_up_to_index from memory and DB.
        Used for user message editing.
        """
        self.messages = self.messages[:keep_up_to_index]
        # Delete all messages in DB that are beyond the kept count
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM messages WHERE session_id = ?
                    ORDER BY id ASC LIMIT ?
                )
            """, (self.session_id, self.session_id, keep_up_to_index))
            conn.commit()

    def clear(self):
        self.messages.clear()
        self.db.clear_session_messages(self.session_id)

    def export_to_json(self, file_path: Optional[str] = None) -> str:
        """Exports the conversation history to a JSON file."""
        if file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            conv_dir = os.path.join(base_dir, "data", "conversations")
            os.makedirs(conv_dir, exist_ok=True)
            file_path = os.path.join(conv_dir, f"{self.session_id}.json")

        payload = {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "exported_at": datetime.utcnow().isoformat(),
            "messages": [m.to_dict() for m in self.messages]
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return file_path

    def import_from_json(self, file_path: str):
        """Imports conversation history from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.clear()
        self.session_id = data.get("session_id", self.session_id)
        self.system_prompt = data.get("system_prompt", self.system_prompt)
        for m in data.get("messages", []):
            self.add_message(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                token_count=m.get("token_count", 0),
                metadata=m.get("metadata", {})
            )
