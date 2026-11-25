"""
MapView — real map via Leaflet + OpenStreetMap (CartoDB dark tiles).
100% free, no API key, no credit card.

Falls back to None if QWebEngineView is unavailable (caller should then
use the hand-drawn MapWidget instead).
"""
from PyQt5.QtCore import QUrl

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    _WEB_OK = True
except Exception:
    _WEB_OK = False


# Leaflet + CartoDB dark tiles (both free, keyless). Dark theme matches the UI.
_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map { height:100%; margin:0; background:#0a0e1a; }
  .car-icon {
    background:#00aaff; width:18px; height:18px; border-radius:50%;
    border:2px solid #fff; box-shadow:0 0 12px #00aaff;
  }
  .pulse {
    animation: pulse 1.5s infinite;
  }
  @keyframes pulse {
    0%   { box-shadow:0 0 0 0 rgba(0,170,255,0.5); }
    70%  { box-shadow:0 0 0 14px rgba(0,170,255,0); }
    100% { box-shadow:0 0 0 0 rgba(0,170,255,0); }
  }
  .leaflet-popup-content-wrapper, .leaflet-popup-tip {
    background:#0d1f3a; color:#a0c8ff; border:1px solid #1a3a6a;
  }
</style>
</head>
<body>
<div id="map"></div>
<script>
  var LAT = __LAT__, LON = __LON__;
  var map = L.map('map', { zoomControl:true, attributionControl:false })
             .setView([LAT, LON], 14);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains:'abcd'
  }).addTo(map);

  // Car marker (current location)
  var carIcon = L.divIcon({ className:'', html:'<div class="car-icon pulse"></div>',
                            iconSize:[18,18], iconAnchor:[9,9] });
  var car = L.marker([LAT, LON], { icon:carIcon }).addTo(map)
             .bindPopup('現在地');

  // Destination marker (slightly offset for demo)
  var dest = L.marker([LAT+0.012, LON+0.014]).addTo(map).bindPopup('🏫 HAL東京');

  // Route line (car → destination)
  var route = L.polyline([[LAT,LON],[LAT+0.006,LON+0.005],[LAT+0.012,LON+0.014]],
                         { color:'#00aaff', weight:4, opacity:0.7, dashArray:'8,8' }).addTo(map);

  // Danger markers — redrawn around the car's real position
  var dangerGroup = L.layerGroup().addTo(map);
  function redrawDangers(lat, lon) {
    dangerGroup.clearLayers();
    var items = [
      [lat+0.004, lon+0.006, '#ff2828', '⚠ 事故発生 1.2km先'],
      [lat+0.002, lon+0.003, '#ff8c00', '⚡ 急ブレーキ 0.8km先'],
      [lat-0.003, lon+0.002, '#ffcc00', '≡ 渋滞情報 3.5km先']
    ];
    items.forEach(function(d) {
      L.circleMarker([d[0],d[1]], { radius:8, color:d[2], fillColor:d[2],
        fillOpacity:0.8, weight:2 }).bindPopup(d[3]).addTo(dangerGroup);
    });
  }
  redrawDangers(LAT, LON);

  // API for Python to move the car marker in real time
  window.updateCar = function(lat, lon) {
    car.setLatLng([lat, lon]);
    redrawDangers(lat, lon);
    map.panTo([lat, lon]);
  };

  // Recenter map + car without reloading the page (avoids race with drawRoute)
  window.recenter = function(lat, lon) {
    car.setLatLng([lat, lon]);
    redrawDangers(lat, lon);
    map.setView([lat, lon], 15);
  };

  // API for Python to draw the REAL OSRM route (replaces the demo line)
  window.drawRoute = function(coords, dLat, dLon, dName) {
    if (route) { map.removeLayer(route); }
    route = L.polyline(coords, { color:'#00aaff', weight:5, opacity:0.9 }).addTo(map);
    car.setLatLng(coords[0]);
    redrawDangers(coords[0][0], coords[0][1]);
    dest.setLatLng([dLat, dLon]).bindPopup('🏫 ' + (dName || 'HAL東京'));
    // Keep the view focused around the car (like a real GPS), zoom 15
    map.setView(coords[0], 15);
  };
</script>
</body>
</html>"""


def is_available() -> bool:
    return _WEB_OK


if _WEB_OK:
    class MapView(QWebEngineView):
        def __init__(self, lat: float = 35.6895, lon: float = 139.6917, parent=None):
            super().__init__(parent)
            self.setMinimumHeight(260)
            self._ready: bool = False
            self._pending: list = []          # JS queued until the page loads
            self.loadFinished.connect(self._on_loaded)
            self._load(lat, lon)

        def _load(self, lat: float, lon: float):
            html = _HTML.replace("__LAT__", str(lat)).replace("__LON__", str(lon))
            self.setHtml(html, QUrl("https://localhost/"))

        def _on_loaded(self, ok: bool):
            self._ready = True
            for js in self._pending:
                self.page().runJavaScript(js)
            self._pending.clear()

        def _run(self, js: str):
            """Run JS now if the page is ready, else queue it until loadFinished."""
            if self._ready:
                self.page().runJavaScript(js)
            else:
                self._pending.append(js)

        def set_location(self, lat: float, lon: float):
            """Re-center map + car marker (no reload → no race with draw_route)."""
            self._run(f"window.recenter && window.recenter({lat},{lon});")

        def update_car(self, lat: float, lon: float):
            """Move just the car marker (real-time)."""
            self._run(f"window.updateCar && window.updateCar({lat},{lon});")

        def draw_route(self, coords: list, dest_lat: float, dest_lon: float, dest_name: str = "HAL東京"):
            """Draw the real OSRM route polyline. coords = [[lat, lon], ...]."""
            import json
            self._run(
                f"window.drawRoute && window.drawRoute("
                f"{json.dumps(coords)}, {dest_lat}, {dest_lon}, "
                f"{json.dumps(dest_name, ensure_ascii=True)});"
            )
else:
    MapView = None
