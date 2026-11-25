"""
RouteService — real driving route via OSRM (free public server, no key).

Given origin + destination (lat/lon), returns the real road route:
  • distance_km   — real distance
  • duration_min  — real driving time
  • coords        — [[lat, lon], ...] route polyline for the map

Runs in a QThread; fails silently (keeps simulated nav) when offline.

Signal:
  route_ready(dict) — {distance_km, duration_min, coords, dest_name}
"""
import json
import urllib.request
from PyQt5.QtCore import QThread, pyqtSignal

_OSRM = "http://router.project-osrm.org/route/v1/driving"


class RouteService(QThread):
    route_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._job: dict = {}
        self._last: dict | None = None

    @property
    def last(self) -> dict | None:
        return self._last

    def request(self, o_lat, o_lon, d_lat, d_lon, dest_name="目的地"):
        if self.isRunning():
            return
        self._job = {
            "o_lat": o_lat, "o_lon": o_lon,
            "d_lat": d_lat, "d_lon": d_lon,
            "dest_name": dest_name,
        }
        self.start()

    def run(self):
        j = self._job
        try:
            url = (
                f"{_OSRM}/{j['o_lon']},{j['o_lat']};{j['d_lon']},{j['d_lat']}"
                f"?overview=simplified&geometries=geojson"
            )
            data  = json.load(urllib.request.urlopen(url, timeout=12))
            route = data["routes"][0]
            # OSRM returns [lon, lat]; Leaflet wants [lat, lon]
            coords = [[c[1], c[0]] for c in route["geometry"]["coordinates"]]
            result = {
                "distance_km":  round(route["distance"] / 1000, 1),
                "duration_min": max(1, round(route["duration"] / 60)),
                "coords":       coords,
                "dest_name":    j["dest_name"],
                "dest_lat":     j["d_lat"],
                "dest_lon":     j["d_lon"],
                "live":         True,
            }
            self._last = result
            self.route_ready.emit(result)
        except Exception:
            pass   # offline / OSRM down → keep simulated navigation
