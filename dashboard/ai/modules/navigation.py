"""
Module 6 — ナビゲーション支援 (Navigation)
Current Location / Destination Search / Route Guidance / ETA / Route Suggestion
"""
import random
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


# ── Simulated POI database ─────────────────────────────────────────────────────
_PLACES = {
    "HAL東京":      {"lat": 35.685, "lon": 139.753, "type": "school"},
    "東京駅":        {"lat": 35.681, "lon": 139.767, "type": "station"},
    "新宿":          {"lat": 35.689, "lon": 139.700, "type": "area"},
    "渋谷":          {"lat": 35.658, "lon": 139.701, "type": "area"},
    "コンビニ":       {"lat": 35.683, "lon": 139.755, "type": "convenience"},
    "ガソリンスタンド": {"lat": 35.680, "lon": 139.748, "type": "fuel"},
    "病院":          {"lat": 35.690, "lon": 139.760, "type": "hospital"},
}

_ROUTE_MESSAGES = [
    "次の交差点を右折してください。",
    "300m先を左折です。",
    "目的地周辺に到着しました。",
    "ルートを再計算中...",
]


class Navigation(QObject):
    """
    Navigation assistant.
    Emits:
      eta_update(str)        — periodic ETA reminder
      route_alert(str)       — traffic / route deviation warning
    """
    eta_update  = pyqtSignal(str)
    route_alert = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_loc  = {"lat": 35.682, "lon": 139.750, "name": "現在地"}
        self._destination: dict | None = None
        self._eta_min: int = 0
        self._guidance_active = False
        self._elapsed = 0
        self._live_route: dict | None = None   # real OSRM route (distance/duration)

        self._eta_timer = QTimer(self)
        self._eta_timer.timeout.connect(self._tick_eta)

    def set_live_route(self, route: dict):
        """Store the real OSRM route so replies use real distance/ETA."""
        self._live_route = route

    # ── Navigation control ────────────────────────────────────────────────────
    def start_navigation(self, destination: str) -> str:
        dest_info = self._find_place(destination)
        self._destination = {"name": destination, **dest_info}
        self._elapsed     = 0
        self._guidance_active = True
        self._eta_timer.start(60_000)   # update every minute

        # Use real OSRM route if available, else fall back to a rough estimate
        if self._live_route:
            self._eta_min = self._live_route["duration_min"]
            dist = self._live_route["distance_km"]
            return (
                f"{destination}まで案内開始！"
                f"距離{dist}km、約{self._eta_min}分で到着予定だよ。"
            )
        self._eta_min = random.randint(8, 30)
        return f"{destination}まで案内を開始するよ！約{self._eta_min}分で到着予定。"

    def stop_navigation(self) -> str:
        self._guidance_active = False
        self._destination = None
        self._eta_timer.stop()
        return "ナビを終了したよ。"

    def _tick_eta(self):
        if not self._guidance_active:
            return
        self._elapsed  += 1
        remaining       = max(0, self._eta_min - self._elapsed)
        if remaining == 0:
            self.route_alert.emit(f"{self._destination['name']}に到着だよ！")
            self.stop_navigation()
        elif remaining in (10, 5, 2):
            self.eta_update.emit(f"あと{remaining}分で{self._destination['name']}に着くよ！")

    # ── Queries ───────────────────────────────────────────────────────────────
    def destination_reply(self, query: str) -> str:
        for name in _PLACES:
            if name in query:
                return self.start_navigation(name)
        return self.start_navigation(
            self._destination["name"] if self._destination else "HAL東京"
        )

    def eta_reply(self) -> str:
        if not self._guidance_active or not self._destination:
            # Even without active nav, report the precomputed real route if any
            if self._live_route:
                r = self._live_route
                return f"{r['dest_name']}まで距離{r['distance_km']}km、約{r['duration_min']}分だよ。"
            return "ナビは起動していないよ。どこかに向かう？"
        remaining = max(0, self._eta_min - self._elapsed)
        dist = f"（残り{self._live_route['distance_km']}km）" if self._live_route else ""
        return f"{self._destination['name']}まであと約{remaining}分{dist}だよ！"

    def location_reply(self) -> str:
        return f"現在地：{self._current_loc['name']} 付近だよ。"

    def route_suggestion(self, speed: int, risk: int) -> str:
        if risk >= 60:
            return "前方にリスクがあるよ。安全なルートに変更する？"
        if speed < 20:
            return "渋滞中みたい。高速道路に切り替えようか？"
        return "今のルートが最適だよ。このまま進んでね！"

    def nearby_reply(self, category: str) -> str:
        matches = [n for n, p in _PLACES.items() if category in p.get("type", "")]
        if matches:
            return f"近くに「{matches[0]}」があるよ。案内する？"
        return f"近くに{category}は見つからなかったよ。"

    def _find_place(self, name: str) -> dict:
        for pname, info in _PLACES.items():
            if pname in name or name in pname:
                return info
        return {"lat": 35.685, "lon": 139.750, "type": "unknown"}

    @property
    def is_navigating(self) -> bool:
        return self._guidance_active

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        if self._guidance_active and self._destination:
            remaining = max(0, self._eta_min - self._elapsed)
            dist = f", {self._live_route['distance_km']}km" if self._live_route else ""
            return f"Navigation active → {self._destination['name']}, ETA {remaining} min{dist}"
        if self._live_route:
            r = self._live_route
            return f"Route ready → {r['dest_name']}: {r['distance_km']}km, {r['duration_min']}min (real)"
        return "Navigation: inactive"
