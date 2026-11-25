"""
Module 2 — AI対話 (Conversation)
Free Chat / Question Answering / Context Memory / Multi-turn
"""
from datetime import datetime


class ConversationMemory:
    """
    Stores the full multi-turn conversation history.
    Used by NeuroAgent to maintain context across turns.
    """
    MAX_TURNS = 30   # keep last 30 user+assistant pairs (60 messages)

    def __init__(self):
        self._history: list[dict] = []   # [{role, content, timestamp}]
        self._session_start = datetime.now()

    # ── History management ────────────────────────────────────────────────────
    def add_user(self, text: str):
        self._history.append({
            "role":      "user",
            "content":   text,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        self._trim()

    def add_assistant(self, text: str):
        self._history.append({
            "role":      "assistant",
            "content":   text,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        self._trim()

    def _trim(self):
        max_msg = self.MAX_TURNS * 2
        if len(self._history) > max_msg:
            self._history = self._history[-max_msg:]

    def clear(self):
        self._history.clear()
        self._session_start = datetime.now()

    # ── Export for Claude API ─────────────────────────────────────────────────
    def for_api(self) -> list[dict]:
        """Return list of {role, content} for Claude messages parameter."""
        return [{"role": m["role"], "content": m["content"]} for m in self._history]

    # ── Stats ─────────────────────────────────────────────────────────────────
    @property
    def turn_count(self) -> int:
        return sum(1 for m in self._history if m["role"] == "user")

    @property
    def session_duration(self) -> str:
        delta = datetime.now() - self._session_start
        mins  = int(delta.total_seconds() / 60)
        return f"{mins}分"

    def last_user_msg(self) -> str | None:
        for m in reversed(self._history):
            if m["role"] == "user":
                return m["content"]
        return None

    def last_assistant_msg(self) -> str | None:
        for m in reversed(self._history):
            if m["role"] == "assistant":
                return m["content"]
        return None

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        return (
            f"Conversation turns: {self.turn_count}\n"
            f"Session duration: {self.session_duration}"
        )
