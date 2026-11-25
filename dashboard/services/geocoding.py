"""
GeocodeService — turn any place name into coordinates.
Uses Nominatim (OpenStreetMap), free and keyless.

Nominatim usage policy: send a User-Agent, max ~1 req/sec. We respect both.

Signals:
  found(dict)   — {name, lat, lon, display}
  not_found(str)— the query that returned nothing / errored
"""
import json
import urllib.request
import urllib.parse
from PyQt5.QtCore import QThread, pyqtSignal

_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_HEADERS   = {"User-Agent": "Core4Drive/1.0 (car assistant demo)"}


class GeocodeService(QThread):
    found     = pyqtSignal(dict)
    not_found = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""
        self._pending_query = None
        self._viewbox = None   # (lat, lon) center for nearby search, or None
        self.finished.connect(self._on_finished)

    def _on_finished(self):
        if self._pending_query:
            q = self._pending_query
            self._pending_query = None
            self.search(q)

    def search(self, query: str):
        """Global place search (anywhere)."""
        if not query.strip():
            return
        if self.isRunning():
            self._pending_query = query.strip()
            return
        self._query = query.strip()
        self._pending_query = None
        self._viewbox = None
        self.start()

    def search_nearby(self, keyword: str, lat: float, lon: float):
        """Find a place of `keyword` type near (lat, lon) — e.g. ラーメン, カフェ."""
        if self.isRunning() or not keyword.strip():
            return
        self._query = keyword.strip()
        self._viewbox = (lat, lon)
        self.start()

    def run(self):
        q = self._query
        try:
            params = {"q": q, "format": "json", "limit": 1, "accept-language": "ja"}
            # Bias/bound the search to a ~3km box around the car when nearby
            if self._viewbox:
                lat, lon = self._viewbox
                d = 0.03
                params["viewbox"] = f"{lon-d},{lat+d},{lon+d},{lat-d}"
                params["bounded"] = 1
            url = f"{_NOMINATIM}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers=_HEADERS)
            data = json.load(urllib.request.urlopen(req, timeout=10))
            if not data:
                self.not_found.emit(q)
                return
            top = data[0]
            display = top.get("display_name", q)
            short   = display.split(",")[0].strip() or q
            self.found.emit({
                "name":    short,
                "display": display,
                "lat":     float(top["lat"]),
                "lon":     float(top["lon"]),
                "nearby":  bool(self._viewbox),
            })
        except Exception:
            self.not_found.emit(q)
