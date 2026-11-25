"""
Module 4 — 情報提供 (Information)
Time / Weather / News / Calendar / Reminder
"""
import random
from datetime import datetime, date


# ── Simulated data (swap for real APIs later) ──────────────────────────────────
_WEATHER_DATA = random.choice([
    {"cond": "晴れ",        "temp": 24, "hum": 45, "uv": "中",  "advice": "絶好のドライブ日和！"},
    {"cond": "くもり",       "temp": 20, "hum": 68, "uv": "低",  "advice": "雨具を用意しておいてね。"},
    {"cond": "小雨",         "temp": 17, "hum": 85, "uv": "なし","advice": "路面が滑りやすいよ。"},
    {"cond": "晴れ時々くもり","temp": 27, "hum": 50, "uv": "高",  "advice": "こまめに水分補給してね。"},
])

_NEWS_HEADLINES = [
    "東京都、来週から新しい交通規制を施行",
    "高速道路 A1区間で工事予定 — 夜間通行止め",
    "自動運転技術の実証実験、来月より開始",
    "ガソリン価格、今週は前週比2円安",
    "大型台風が接近中 — 今週末の外出に注意",
]


class Information:
    """Provides time, weather, news, calendar events, and reminders."""

    def __init__(self):
        self._reminders: list[dict] = []
        self._calendar:  list[dict] = [
            {"date": date.today().isoformat(), "title": "HAL東京 授業",     "time": "10:00"},
            {"date": date.today().isoformat(), "title": "ランチミーティング", "time": "12:30"},
        ]
        self._live_weather: dict | None = None   # set by WeatherService when online

    def set_live_weather(self, data: dict):
        """Called when real weather arrives from WeatherService."""
        self._live_weather = data

    def _weather(self) -> dict:
        """Live weather if available, else simulated fallback."""
        return self._live_weather or _WEATHER_DATA

    # ── Time ──────────────────────────────────────────────────────────────────
    @staticmethod
    def now_str() -> str:
        now = datetime.now()
        wd  = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]
        return f"{now.strftime('%H:%M')} ({now.strftime('%m/%d')} {wd}曜日)"

    def time_reply(self) -> str:
        return f"今は{self.now_str()}だよ。"

    # ── Weather ───────────────────────────────────────────────────────────────
    def get_weather(self) -> dict:
        return self._weather()

    def weather_reply(self, detail: bool = False) -> str:
        w = self._weather()
        live = "（リアルタイム）" if w.get("live") else ""
        brief = f"今{w['cond']}で{w['temp']}°Cだよ{live}。{w['advice']}"
        if not detail:
            return brief
        extra = f"湿度{w['hum']}%"
        if w.get("wind") is not None:
            extra += f"、風速{w['wind']}km/h"
        elif w.get("uv"):
            extra += f"、UV指数{w['uv']}"
        return f"{brief}\n{extra}。"

    # ── News ──────────────────────────────────────────────────────────────────
    @staticmethod
    def news_reply() -> str:
        headline = random.choice(_NEWS_HEADLINES)
        return f"最新ニュース：「{headline}」"

    # ── Calendar ──────────────────────────────────────────────────────────────
    def today_schedule(self) -> str:
        today = date.today().isoformat()
        events = [e for e in self._calendar if e["date"] == today]
        if not events:
            return "今日の予定は特にないよ！"
        items = "、".join(f"{e['time']} {e['title']}" for e in events)
        return f"今日の予定：{items}"

    def add_event(self, title: str, time_str: str = "", day: str = None) -> str:
        self._calendar.append({
            "date":  day or date.today().isoformat(),
            "title": title,
            "time":  time_str or "未定",
        })
        return f"「{title}」を予定に追加したよ！"

    # ── Reminder ──────────────────────────────────────────────────────────────
    def add_reminder(self, text: str) -> str:
        now = datetime.now().strftime("%H:%M")
        self._reminders.append({"time": now, "text": text})
        return f"「{text}」を覚えておくね！"

    def list_reminders(self) -> str:
        if not self._reminders:
            return "メモはまだないよ。"
        items = "、".join(r["text"] for r in self._reminders[-3:])
        return f"メモ：{items}"

    def clear_reminders(self) -> str:
        self._reminders.clear()
        return "メモを全部消したよ。"

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        w = self._weather()
        return (
            f"Time: {self.now_str()}\n"
            f"Weather: {w['cond']}, {w['temp']}°C, humidity {w['hum']}%\n"
            f"Schedule: {len(self._calendar)} events today\n"
            f"Reminders: {len(self._reminders)} active"
        )
