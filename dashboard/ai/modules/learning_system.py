"""
Module 9 — 学習機能 (Learning System)
Destination Pattern / Driving Pattern / Usage Pattern
/ Favorite Function / Personalized AI Growth
"""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, date
from config import HABITS_FILE


class LearningSystem:
    """
    Observes all user interactions and learns patterns over time.
    Grows more personalized with each session.
    """

    def __init__(self):
        self._events:  list[dict] = []
        self._session: dict       = {
            "start":      datetime.now().isoformat(),
            "actions":    [],
            "destinations": [],
            "queries":    [],
        }
        self._profile: dict = self._load_profile()

    # ── Profile persistence ───────────────────────────────────────────────────
    def _load_profile(self) -> dict:
        try:
            with open(HABITS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw.get("learned_profile", self._empty_profile())
        except Exception:
            return self._empty_profile()

    @staticmethod
    def _empty_profile() -> dict:
        return {
            "destination_patterns":  {},   # {dest: count}
            "hourly_activity":       {},   # {"HH": count}
            "function_frequency":    {},   # {function: count}
            "driving_stats": {
                "total_sessions": 0,
                "avg_speed":      0.0,
                "avg_risk":       0.0,
                "speed_samples":  [],
            },
            "favorite_functions":    [],
            "personalization_level": 0,    # 0-100
        }

    def save(self):
        try:
            with open(HABITS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = {}
        raw["learned_profile"] = self._profile
        try:
            with open(HABITS_FILE, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── Event recording ───────────────────────────────────────────────────────
    def record_action(self, action: str, context: dict = None):
        """Record any user action for learning."""
        now   = datetime.now()
        event = {
            "action":  action,
            "hour":    now.hour,
            "weekday": now.weekday(),
            "ts":      now.isoformat(),
            **(context or {}),
        }
        self._events.append(event)
        self._session["actions"].append(action)
        if len(self._events) > 500:
            self._events = self._events[-500:]

        # Update hourly activity
        hk = f"{now.hour:02d}"
        self._profile["hourly_activity"][hk] = \
            self._profile["hourly_activity"].get(hk, 0) + 1

        # Update function frequency
        self._profile["function_frequency"][action] = \
            self._profile["function_frequency"].get(action, 0) + 1

        self._update_favorites()
        self._update_personalization()

    def record_destination(self, destination: str):
        dp = self._profile["destination_patterns"]
        dp[destination] = dp.get(destination, 0) + 1
        self._session["destinations"].append(destination)
        self.save()

    def record_speed(self, speed: int, risk: int):
        ds = self._profile["driving_stats"]
        samples = ds.get("speed_samples", [])
        samples.append(speed)
        if len(samples) > 200:
            samples = samples[-200:]
        ds["speed_samples"] = samples
        ds["avg_speed"]     = round(sum(samples) / len(samples), 1)
        ds["avg_risk"]      = round(
            (ds.get("avg_risk", 0) * (len(samples) - 1) + risk) / len(samples), 1
        )

    def record_query(self, query: str):
        self._session["queries"].append(query)

    # ── Pattern analysis ──────────────────────────────────────────────────────
    def _update_favorites(self):
        freq = self._profile["function_frequency"]
        top  = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        self._profile["favorite_functions"] = [f for f, _ in top]

    def _update_personalization(self):
        score = 0
        if len(self._profile["destination_patterns"]) >= 3:  score += 20
        if self._profile["driving_stats"]["avg_speed"] > 0:   score += 20
        if len(self._profile["favorite_functions"])  >= 3:    score += 20
        if len(self._profile["hourly_activity"])     >= 5:    score += 20
        if self._profile["driving_stats"]["total_sessions"] >= 3: score += 20
        self._profile["personalization_level"] = score

    def end_session(self):
        self._profile["driving_stats"]["total_sessions"] += 1
        self.save()

    # ── Learned insights ──────────────────────────────────────────────────────
    @property
    def top_destination(self) -> str | None:
        dp = self._profile["destination_patterns"]
        return max(dp, key=dp.get) if dp else None

    @property
    def peak_hour(self) -> str | None:
        ha = self._profile["hourly_activity"]
        return max(ha, key=ha.get) if ha else None

    @property
    def favorite_function(self) -> str | None:
        ff = self._profile["favorite_functions"]
        return ff[0] if ff else None

    @property
    def personalization_level(self) -> int:
        return self._profile.get("personalization_level", 0)

    @property
    def avg_speed(self) -> float:
        return self._profile["driving_stats"].get("avg_speed", 0.0)

    # ── Smart suggestions based on learned data ────────────────────────────────
    def smart_suggestion(self, hour: int = None, speed: int = 0, risk: int = 0) -> str | None:
        h   = hour or datetime.now().hour
        top = self.top_destination
        fav = self.favorite_function

        if risk >= 75:
            return "リスクが高いよ！安全運転に集中して！"

        # Destination suggestion at usual travel time
        if top:
            peak = int(self.peak_hour or "8")
            if abs(h - peak) <= 1:
                return f"いつものように{top}に向かう時間だよ。ナビを起動する？"

        # Favorite function reminder
        if fav == "music_play" and h in range(7, 22):
            return "音楽をかけながらドライブしよう！"

        return None

    # ── Personalized greeting ─────────────────────────────────────────────────
    def personalized_greeting(self) -> str:
        lvl = self.personalization_level
        top = self.top_destination or "HAL東京"
        avg = self.avg_speed

        if lvl >= 80:
            return f"おかえり！{top}にまた行くの？いつもの道で案内するよ。"
        if lvl >= 40:
            return f"やあ！最近よく行く{top}に案内しようか？"
        return "こんにちは！どこかに行く？"

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        lvl = self.personalization_level
        top = self.top_destination or "unknown"
        fav = self.favorite_function or "unknown"
        return (
            f"Personalization level: {lvl}/100\n"
            f"Top destination: {top} | Favorite function: {fav}\n"
            f"Avg speed: {self.avg_speed} km/h | "
            f"Sessions: {self._profile['driving_stats']['total_sessions']}"
        )
