"""
CarLink — connects Core-4 Drive to the real smart_ai_car_servo (Raspberry Pi
+ Arduino) over its FastAPI pi_server (services/car_link ↔ pi_server/main.py).

Polls GET /api/status once per second for real telemetry (speed, obstacle
distance, motor battery, hazard flags). Falls back silently to simulated
dashboard data if the car/server is unreachable — same offline-safe pattern
as WeatherService / RouteService.

Signals:
  status_ready(dict)        — raw /api/status payload
  connection_changed(bool)  — True once the car answers, False if it drops
"""
import json
import threading
import urllib.request
from PyQt5.QtCore import QThread, pyqtSignal


class CarLink(QThread):
    status_ready       = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self, base_url: str = "http://127.0.0.1:8000", parent=None):
        super().__init__(parent)
        self.base_url  = base_url.rstrip("/")
        self._connected = False
        self._running    = True

    @property
    def connected(self) -> bool:
        return self._connected

    def stop_polling(self):
        self._running = False

    # ── Poll loop ────────────────────────────────────────────────────────────
    def run(self):
        while self._running:
            try:
                with urllib.request.urlopen(f"{self.base_url}/api/status", timeout=1.5) as r:
                    data = json.load(r)
                if not self._connected:
                    self._connected = True
                    self.connection_changed.emit(True)
                self.status_ready.emit(data)
            except Exception:
                if self._connected:
                    self._connected = False
                    self.connection_changed.emit(False)
            self.msleep(1000)

    # ── Commands (fire-and-forget, never block the UI thread) ─────────────────
    def _post(self, path: str, payload: dict | None = None):
        def _send():
            try:
                body = json.dumps(payload or {}).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}{path}", data=body,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                urllib.request.urlopen(req, timeout=2.0)
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()

    def drive(self, left: int, right: int):
        self._post("/api/drive", {"left": left, "right": right})

    def stop_car(self):
        self._post("/api/stop")

    def beep(self, ms: int = 140):
        self._post("/api/beep", {"ms": ms})

    def look(self, where: str):
        self._post(f"/api/look/{where.lower()}")
