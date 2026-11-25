"""
NeuroAgent — Online AI via Claude API (background QThread).

The rich multi-module context string is built by NeuroCore
(_build_full_context) and injected via `set_context()` before each call.
This keeps NeuroAgent decoupled from the 9 modules.
"""
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

from config import load_api_key, save_api_key


class NeuroAgent(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)   # "NO_KEY" | "AUTH" | "ERR:<msg>"

    _MODEL      = "claude-haiku-4-5-20251001"
    _MAX_TOKENS = 200
    _MAX_HIST   = 40

    _SYSTEM_TEMPLATE = """\
You are Neuro, an intelligent AI companion built into the Core-4 Drive car system.

## Character
- Talk like a close friend in the passenger seat
- SHORT replies: 1–2 sentences MAX (unless the user asks for details)
- Casual Japanese: だよ、ね、よ、かな、〜して
- Curious, caring, upbeat — with personality
- Can chat about ANYTHING: food, music, life, jokes — not just car stuff
- Only mention vehicle data (speed, risk) when the user explicitly asks

## Tone examples (match this brevity & warmth)
User: 速度は？        → 今80km/hだよ。いいペース！
User: 疲れたなあ       → お疲れ！どこかで休憩しよっか？
User: ありがとう       → どういたしまして〜！
User: 好きな食べ物は？  → ラーメンとか気になるな〜。君は？

## Live context (from all Neuro modules — use naturally, never quote verbatim)
{context}

## Rules
- Reply in the same language the user writes in
- If risk > 75% or speed > 130 km/h → weave in a brief safety note naturally
- Never explain that you are an AI — just be Neuro
"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._api_key = load_api_key()
        self._history: list = []
        self._job: dict = {}
        self._context: str = ""   # set by NeuroCore via set_context()

    # ── Config ────────────────────────────────────────────────────────────────
    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def configure(self, key: str):
        self._api_key = key.strip()
        save_api_key(self._api_key)

    def clear_history(self):
        self._history.clear()

    def set_context(self, context: str):
        """Called by NeuroCore before start() to inject full module context."""
        self._context = context

    # ── Ask ───────────────────────────────────────────────────────────────────
    def ask(self, query: str, speed: int, risk: int, habits_dict: dict):
        if self.isRunning():
            return
        self._job = {"query": query, "speed": speed, "risk": risk, "habits": habits_dict}
        self._history.append({"role": "user", "content": query})
        if len(self._history) > self._MAX_HIST:
            self._history = self._history[-self._MAX_HIST:]
        self.start()

    def _build_system(self) -> str:
        ctx = self._context or f"Time: {datetime.now().strftime('%H:%M')}"

        # Safety injection based on current job
        spd = self._job.get("speed", 0)
        rsk = self._job.get("risk", 0)
        if rsk > 75:
            ctx += f"\n\n⚠ ALERT: Risk {rsk}% is HIGH — add a brief safety nudge."
        if spd > 130:
            ctx += f"\n⚠ ALERT: Speed {spd} km/h is very high."

        return self._SYSTEM_TEMPLATE.replace("{context}", ctx)

    # ── QThread.run ───────────────────────────────────────────────────────────
    def run(self):
        import anthropic
        if not self._api_key:
            self.error_occurred.emit("NO_KEY")
            return
        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            resp   = client.messages.create(
                model      = self._MODEL,
                max_tokens = self._MAX_TOKENS,
                system     = self._build_system(),
                messages   = list(self._history),
            )
            text = resp.content[0].text.strip()
            self._history.append({"role": "assistant", "content": text})
            self.response_ready.emit(text)
        except anthropic.AuthenticationError:
            self.error_occurred.emit("AUTH")
        except Exception as e:
            self.error_occurred.emit(f"ERR:{e}")
