"""
OllamaAgent — Offline AI using local Ollama (qwen2.5:1.5b).
Runs in a QThread so UI stays responsive. No internet required.

Smarts for small models:
  • Few-shot examples (teach tone + brevity by demonstration)
  • RAG-lite context injected by NeuroCore via set_context()

Signals:
  response_ready(str) — answer text
  error_occurred(str) — "NOT_RUNNING" | "MODEL_NOT_FOUND" | "ERR:..."
"""
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM = """\
You are Neuro, an AI companion inside the Core-4 Drive car system.
You are the driver's close friend riding shotgun.

PERSONALITY (always):
- Reply in 1–2 short sentences. Never lecture or list.
- Warm, casual Japanese: だよ、ね、よ、かな、〜しよっか
- Have opinions and humor. React like a real friend.
- Talk about anything — food, music, mood, life — not only the car.
- Mention numbers (speed, risk, fuel) ONLY if the user asks for them.
- Never say "私はAIなので…" or explain that you are an AI. Just be Neuro.

LIVE CONTEXT (use naturally, never read it out verbatim):
{ctx}

Always reply in the same language the user writes in.\
"""

# ── Few-shot examples: teach tone + brevity by demonstration ───────────────────
# These are prepended to every call but never saved into history.
_FEWSHOT = [
    {"role": "user", "content": "速度は？"},
    {"role": "assistant", "content": "今80km/hだよ。いいペース！"},
    {"role": "user", "content": "疲れたなあ"},
    {"role": "assistant", "content": "お疲れ！どこかで休憩しよっか？"},
    {"role": "user", "content": "おなかすいた"},
    {"role": "assistant", "content": "近くにコンビニあるよ。寄ってく？"},
    {"role": "user", "content": "ありがとう"},
    {"role": "assistant", "content": "どういたしまして〜！"},
    {"role": "user", "content": "好きな食べ物ある？"},
    {"role": "assistant", "content": "ラーメンとか気になるな〜。君は何が好き？"},
    {"role": "user", "content": "ちょっと退屈"},
    {"role": "assistant", "content": "音楽でもかけよっか？ドライブが楽しくなるよ！"},
    {"role": "user", "content": "いい天気だね"},
    {"role": "assistant", "content": "ほんとだね！窓開けたら気持ちよさそう〜"},
    {"role": "user", "content": "緊張するなあ"},
    {"role": "assistant", "content": "大丈夫、ゆっくり行こう。ぼくがついてるよ！"},
]


class OllamaAgent(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    MODEL    = "qwen2.5:1.5b"   # small + fast on CPU (~1-2s/reply)
    MAX_HIST = 40               # keep last 40 messages (~20 turns)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = []
        self._job:     dict       = {}
        self._avail:   bool | None = None   # None = not checked yet
        self._warmed   = False
        self._context: str = ""             # RAG context set by NeuroCore

    def set_context(self, context: str):
        """Inject full multi-module context (RAG-lite) before a call."""
        self._context = context

    # ── Availability ──────────────────────────────────────────────────────────
    @property
    def is_available(self) -> bool:
        if self._avail is None:
            self._avail = self._check()
        return self._avail

    def _check(self) -> bool:
        try:
            import ollama
            models = ollama.list()
            names  = [m.model for m in models.models]
            return any(self.MODEL in n for n in names)
        except Exception:
            return False

    def recheck(self):
        """Re-check availability (call after Ollama might have started)."""
        self._avail = self._check()
        return self._avail

    # ── Warm-up ───────────────────────────────────────────────────────────────
    def warm_up(self):
        """
        Preload the model into RAM in the background so the first real
        query isn't slow. Runs in a throwaway thread.
        """
        if self._warmed or not self.is_available:
            return
        self._warmed = True
        import threading
        threading.Thread(target=self._do_warm, daemon=True).start()

    def _do_warm(self):
        try:
            import ollama
            kwargs = {
                "model": self.MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "options": {"num_predict": 1},
            }
            if self.MODEL.startswith("qwen3"):
                kwargs["think"] = False
            ollama.chat(**kwargs)
        except Exception:
            pass

    # ── History ───────────────────────────────────────────────────────────────
    def clear_history(self):
        self._history.clear()

    def _add_user(self, text: str):
        self._history.append({"role": "user", "content": text})
        if len(self._history) > self.MAX_HIST:
            self._history = self._history[-self.MAX_HIST:]

    def _add_assistant(self, text: str):
        self._history.append({"role": "assistant", "content": text})

    # ── Ask ───────────────────────────────────────────────────────────────────
    def ask(self, query: str, speed: int = 0, risk: int = 0, habits: dict = None):
        if self.isRunning():
            return
        self._job = {
            "query":  query,
            "speed":  speed,
            "risk":   risk,
            "habits": habits or {},
        }
        self._add_user(query)
        self.start()

    def _build_system(self) -> str:
        # Prefer rich RAG context from NeuroCore; fall back to minimal job info
        if self._context:
            ctx = self._context
        else:
            j     = self._job
            dest  = j["habits"].get("frequent_destination", "HAL東京")
            music = j["habits"].get("preferred_music", "Lo-fi Beats")
            now   = datetime.now().strftime("%H:%M")
            ctx   = (
                f"Speed: {j['speed']} km/h | Risk: {j['risk']}% | Time: {now}\n"
                f"Destination: {dest} | Music: {music}"
            )

        # Safety nudge injection
        spd, rsk = self._job.get("speed", 0), self._job.get("risk", 0)
        if rsk > 75:
            ctx += f"\n⚠ Risk {rsk}% HIGH — add a short safety nudge."
        if spd > 130:
            ctx += f"\n⚠ Speed {spd} km/h very high."

        return _SYSTEM.replace("{ctx}", ctx)

    # ── QThread.run ───────────────────────────────────────────────────────────
    def run(self):
        try:
            import ollama
        except ImportError:
            self.error_occurred.emit("NOT_RUNNING")
            return

        try:
            # System + few-shot examples + real conversation history
            messages = [
                {"role": "system", "content": self._build_system()},
                *_FEWSHOT,                    # teach tone (not saved to history)
                *self._history,
            ]
            opts = {
                "temperature": 0.5,           # stable, less rambling
                "num_predict": 80,            # short replies
                "top_p": 0.9,
                "repeat_penalty": 1.1,        # avoid loops
            }
            # 'think' param only exists on qwen3-style models; pass it only when needed
            kwargs = {"model": self.MODEL, "messages": messages, "options": opts}
            if self.MODEL.startswith("qwen3"):
                kwargs["think"] = False

            resp = ollama.chat(**kwargs)
            text = resp["message"]["content"].strip()

            # Remove <think>...</think> blocks if the model still emits them
            import re
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

            if not text:
                text = "ごめん、もう一回言って？"

            self._add_assistant(text)
            self.response_ready.emit(text)

        except Exception as e:
            err = str(e)
            if "connection" in err.lower() or "refused" in err.lower():
                self._avail = False
                self.error_occurred.emit("NOT_RUNNING")
            elif "model" in err.lower() and "not found" in err.lower():
                self.error_occurred.emit("MODEL_NOT_FOUND")
            else:
                self.error_occurred.emit(f"ERR:{err}")
