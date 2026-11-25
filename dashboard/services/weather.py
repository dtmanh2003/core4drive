"""
WeatherService — real weather via Open-Meteo (no API key needed).
Location is auto-detected by IP (ip-api.com). Both are free, keyless.

Runs the network fetch in a QThread so the UI never blocks.
Falls back gracefully (offline → keeps last/default data).

Signal:
  weather_ready(dict) — {cond, temp, hum, wind, advice, city, icon}
"""
import json
import urllib.request
from PyQt5.QtCore import QThread, pyqtSignal


# ── WMO weather_code → Japanese condition / icon / advice ──────────────────────
# https://open-meteo.com/en/docs (WMO Weather interpretation codes)
_WMO = {
    0:  ("晴れ",        "☀", "絶好のドライブ日和！"),
    1:  ("晴れ",        "☀", "いい天気だね！"),
    2:  ("晴れ時々くもり", "🌤", "雲が少し出てるよ。"),
    3:  ("くもり",       "☁", "曇り空だね。"),
    45: ("霧",          "🌫", "霧で視界が悪いよ。ライト点けてね。"),
    48: ("霧",          "🌫", "霧注意！速度を落としてね。"),
    51: ("小雨",        "🌦", "弱い雨だよ。"),
    53: ("小雨",        "🌧", "路面が滑りやすいよ。"),
    55: ("雨",          "🌧", "しっかり降ってるね。"),
    61: ("雨",          "🌧", "雨だよ。ワイパー確認してね。"),
    63: ("雨",          "🌧", "本降りだよ。気をつけて！"),
    65: ("大雨",        "⛈", "大雨！運転に十分注意して！"),
    71: ("雪",          "❄", "雪だよ。スリップ注意！"),
    73: ("雪",          "❄", "雪が積もりそう。慎重にね。"),
    75: ("大雪",        "❄", "大雪！無理せず安全運転を。"),
    80: ("にわか雨",     "🌦", "にわか雨が来てるよ。"),
    81: ("にわか雨",     "🌧", "急な雨に注意！"),
    82: ("激しい雨",     "⛈", "激しい雨！視界に注意して。"),
    95: ("雷雨",        "⛈", "雷雨だよ。安全運転で！"),
    96: ("雷雨",        "⛈", "雷を伴う雨。気をつけてね！"),
    99: ("激しい雷雨",   "⛈", "激しい雷雨！要注意！"),
}


def _interpret(code: int):
    return _WMO.get(code, ("くもり", "☁", "気をつけて運転してね。"))


class WeatherService(QThread):
    weather_ready = pyqtSignal(dict)

    # Default Tokyo coords used if IP lookup fails
    _FALLBACK_LAT = 35.6895
    _FALLBACK_LON = 139.6917

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last: dict | None = None

    @property
    def last(self) -> dict | None:
        return self._last

    def run(self):
        try:
            lat, lon, city = self._locate()
            data = self._fetch_weather(lat, lon, city)
            self._last = data
            self.weather_ready.emit(data)
        except Exception:
            pass   # offline / API down → silently keep simulated data

    # ── Location: saved config → IP fallback ─────────────────────────────────
    def _locate(self):
        from config import load_location
        saved = load_location()
        if saved:
            return saved["lat"], saved["lon"], saved["city"]
        try:
            loc = json.load(urllib.request.urlopen("http://ip-api.com/json/", timeout=6))
            return loc["lat"], loc["lon"], loc.get("city", "現在地")
        except Exception:
            return self._FALLBACK_LAT, self._FALLBACK_LON, "東京"

    # ── Weather by coords ─────────────────────────────────────────────────────
    def _fetch_weather(self, lat, lon, city) -> dict:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m"
        )
        wx = json.load(urllib.request.urlopen(url, timeout=8))
        c  = wx["current"]
        cond, icon, advice = _interpret(int(c["weather_code"]))
        return {
            "cond":   cond,
            "icon":   icon,
            "temp":   round(c["temperature_2m"]),
            "hum":    int(c["relative_humidity_2m"]),
            "wind":   round(c.get("wind_speed_10m", 0)),
            "advice": advice,
            "city":   city,
            "lat":    lat,
            "lon":    lon,
            "live":   True,
        }
