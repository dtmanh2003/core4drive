"""
Module 3 — ユーザー管理 (User Management)
User Profile / User Preference / Habit Learning / Personalized Suggestion
"""
import json
import os
from datetime import datetime
from config import HABITS_FILE


_DEFAULTS = {
    "profile": {
        "name":     "ドライバー",
        "language": "ja",
        "age_group": "adult",   # teen / adult / senior
    },
    "preferences": {
        "tts_enabled":    True,
        "alert_style":    "brief",     # brief | detailed
        "music_genre":    "Lo-fi Beats",
        "nav_voice":      True,
        "dark_mode":      True,
    },
    "habits": {
        "frequent_destination": "HAL東京",
        "preferred_music":      "Lo-fi Beats",
        "driving_style":        "safe",
        "morning_action":       "weather_check",
        "visit_count":          {},
        "last_actions":         [],
        "action_log":           [],
    },
}


class UserManagement:
    """
    Manages user profile, preferences, habits.
    Persists to HABITS_FILE (compatible with HabitLearning).
    """

    def __init__(self):
        self._data = self._load()

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            with open(HABITS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Merge with defaults
            data = json.loads(json.dumps(_DEFAULTS))   # deep copy
            for section in ("profile", "preferences", "habits"):
                if section in raw:
                    data[section].update(raw[section])
                # Also read flat keys (legacy HabitManager format)
            for k in ("frequent_destination", "preferred_music", "driving_style",
                      "morning_action", "visit_count", "last_actions", "action_log"):
                if k in raw:
                    data["habits"][k] = raw[k]
            return data
        except Exception:
            return json.loads(json.dumps(_DEFAULTS))

    def save(self):
        # Read existing file first to preserve learned_profile from LearningSystem
        try:
            with open(HABITS_FILE, "r", encoding="utf-8") as f:
                out = json.load(f)
        except Exception:
            out = {}
        out.update(self._data.get("habits", {}))
        out["profile"]     = self._data.get("profile", {})
        out["preferences"] = self._data.get("preferences", {})
        try:
            with open(HABITS_FILE, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── Profile ───────────────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self._data["profile"].get("name", "ドライバー")

    @property
    def language(self) -> str:
        return self._data["profile"].get("language", "ja")

    def update_profile(self, **kwargs):
        self._data["profile"].update(kwargs)
        self.save()

    # ── Preferences ───────────────────────────────────────────────────────────
    def get_pref(self, key: str, default=None):
        return self._data["preferences"].get(key, default)

    def set_pref(self, key: str, value):
        self._data["preferences"][key] = value
        self.save()

    @property
    def tts_enabled(self) -> bool:
        return self._data["preferences"].get("tts_enabled", True)

    @property
    def preferred_music(self) -> str:
        return self._data["habits"].get("preferred_music", "Lo-fi Beats")

    @property
    def frequent_destination(self) -> str:
        return self._data["habits"].get("frequent_destination", "HAL東京")

    @property
    def habits(self) -> dict:
        """Compatibility accessor so NeuroAI can read habits.habits.get(...)."""
        return self._data["habits"]

    # ── Habit recording ───────────────────────────────────────────────────────
    def record_action(self, action: str, context: dict = None):
        now   = datetime.now()
        entry = {
            "action":  action,
            "hour":    now.hour,
            "weekday": now.weekday(),
            **(context or {}),
        }
        log = self._data["habits"].setdefault("action_log", [])
        log.append(entry)
        if len(log) > 300:
            self._data["habits"]["action_log"] = log[-300:]

        last = self._data["habits"].setdefault("last_actions", [])
        last.append(action)
        if len(last) > 30:
            self._data["habits"]["last_actions"] = last[-30:]

        self.save()

    def record_visit(self, destination: str):
        vc = self._data["habits"].setdefault("visit_count", {})
        vc[destination] = vc.get(destination, 0) + 1
        self.save()

    # ── Personalized suggestion ───────────────────────────────────────────────
    def suggestion(self, hour: int = None, risk: int = 0) -> str:
        h     = hour if hour is not None else datetime.now().hour
        dest  = self.frequent_destination
        music = self.preferred_music
        name  = self.name

        if risk >= 75:
            return f"リスクが高いよ！安全第一で行こう！"
        if 6 <= h < 9:
            return f"おはよう、{name}！{dest}まで案内しようか？"
        if 11 <= h < 13:
            return "お昼近いね。どこかランチに寄る？"
        if 17 <= h < 20:
            return f"お疲れ様！{music}流しながら帰ろうか？"
        return f"いつもの{dest}に向かう？"

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        return (
            f"User: {self.name} | Language: {self.language}\n"
            f"Destination: {self.frequent_destination} | Music: {self.preferred_music}\n"
            f"Alert style: {self.get_pref('alert_style', 'brief')} | "
            f"Driving style: {self._data['habits'].get('driving_style', 'safe')}"
        )
