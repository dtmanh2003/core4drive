from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from config import PANEL_STYLE, load_location, save_location
from widgets.map_widget import MapWidget
from widgets.map_view import MapView, is_available as map_view_available
from services.geocoding import GeocodeService


class RightPanel(QFrame):
    search_requested = pyqtSignal(str)          # user typed a destination
    location_set     = pyqtSignal(float, float, str)  # lat, lon, city

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(PANEL_STYLE)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QLabel("マップ / 共有情報")
        header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        header.setStyleSheet("color: #00aaff; letter-spacing: 2px; border: none;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # ── Location geocoder (background thread) ────────────────────────────
        self._loc_geo = GeocodeService(self)
        self._loc_geo.found.connect(self._on_location_found)
        self._loc_geo.not_found.connect(lambda q: self.show_nav_status(f"📍 「{q}」が見つからないよ"))

        # ── Search box (Google-Maps-like) ────────────────────────────────────
        search_row = QFrame()
        search_row.setStyleSheet("border: none; background: transparent;")
        sr = QHBoxLayout(search_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 目的地を検索 (例: 東京タワー)")
        self.search_input.setStyleSheet(
            "background: #0a1525; color: #d0e0ff; border: 1px solid #1a3060; "
            "border-radius: 8px; padding: 7px 12px; font-size: 11px;"
        )
        self.search_input.returnPressed.connect(self._emit_search)
        sr.addWidget(self.search_input)
        go_btn = QPushButton("案内")
        go_btn.setFixedWidth(48)
        go_btn.setStyleSheet(
            "background: #003880; color: #80c8ff; border: 1px solid #0060cc; "
            "border-radius: 8px; padding: 7px 0; font-weight: bold; font-size: 11px;"
        )
        go_btn.clicked.connect(self._emit_search)
        sr.addWidget(go_btn)

        self.loc_btn = QPushButton("📍")
        self.loc_btn.setFixedWidth(34)
        self.loc_btn.setToolTip("現在地として設定")
        self.loc_btn.setStyleSheet(
            "background: #0a2010; color: #40c060; border: 1px solid #206030; "
            "border-radius: 8px; padding: 7px 0; font-size: 14px;"
        )
        self.loc_btn.clicked.connect(self._set_as_location)
        sr.addWidget(self.loc_btn)
        layout.addWidget(search_row)

        # Show saved location name on startup
        saved = load_location()
        if saved:
            self._loc_label = QLabel(f"📍 現在地: {saved['city']}")
        else:
            self._loc_label = QLabel("📍 現在地: IPから自動取得中")
        self._loc_label.setStyleSheet("color: #3a6a3a; font-size: 9px; border: none;")
        layout.addWidget(self._loc_label)

        # Nav status line (search/route feedback)
        self.nav_status_label = QLabel("")
        self.nav_status_label.setStyleSheet("color: #6080b0; font-size: 9px; border: none;")
        self.nav_status_label.setVisible(False)
        layout.addWidget(self.nav_status_label)

        route_frame = QFrame()
        route_frame.setStyleSheet("background: #0a1525; border: 1px solid #1a2a4a; border-radius: 8px;")
        rl = QHBoxLayout(route_frame)
        rl.setContentsMargins(10, 8, 10, 8)
        self._route_values = {}
        for key, icon, label, val in [
            ("dest", "📍", "目的地", "HAL 東京"),
            ("dist", "🛣", "距離",   "—"),
            ("eta",  "🕐", "到着予定", "—"),
        ]:
            col = QVBoxLayout()
            il = QLabel(f"{icon} {label}")
            il.setStyleSheet("color: #6070a0; font-size: 9px; border: none;")
            vl = QLabel(val)
            vl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            vl.setStyleSheet("color: #d0e0ff; border: none;")
            col.addWidget(il)
            col.addWidget(vl)
            rl.addLayout(col)
            self._route_values[key] = vl
        layout.addWidget(route_frame)

        # Real OSM map if web engine is available, else hand-drawn fallback
        if map_view_available():
            self.map_widget = MapView()
            self.is_real_map = True
        else:
            self.map_widget = MapWidget()
            self.is_real_map = False
        self.map_widget.setStyleSheet("border: 1px solid #1a2a4a; border-radius: 8px;")
        layout.addWidget(self.map_widget)

        dh = QHBoxLayout()
        dh_lbl = QLabel("周辺車両・危険情報")
        dh_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        dh_lbl.setStyleSheet("color: #d0e0ff; border: none;")
        dh.addWidget(dh_lbl)
        detail_btn = QPushButton("詳細 →")
        detail_btn.setStyleSheet("background: transparent; color: #00aaff; border: none; font-size: 9px;")
        dh.addWidget(detail_btn, alignment=Qt.AlignRight)
        layout.addLayout(dh)

        for icon, color, title, sub, time in [
            ("⚠", "#ff2828", "事故発生",    "1.2 km先 / 右車線", "10:29 AM"),
            ("⚡", "#ff8c00", "急ブレーキ検知", "0.8 km先",         "10:29 AM"),
            ("≡", "#ffcc00", "渋滞情報",    "3.5 km先 / 走行中", "10:28 AM"),
        ]:
            layout.addWidget(self._alert_item(icon, color, title, sub, time))

        layout.addStretch()

    def _alert_item(self, icon, color, title, sub, time):
        frame = QFrame()
        frame.setStyleSheet(
            f"background: #0a1525; border-left: 3px solid {color}; "
            "border-top: 1px solid #1a2a4a; border-right: 1px solid #1a2a4a; "
            "border-bottom: 1px solid #1a2a4a; border-radius: 6px;"
        )
        hl = QHBoxLayout(frame)
        hl.setContentsMargins(10, 6, 10, 6)
        hl.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 14))
        icon_lbl.setStyleSheet(f"color: {color}; border: none;")
        icon_lbl.setFixedWidth(20)
        hl.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 10, QFont.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        s = QLabel(sub)
        s.setStyleSheet("color: #8090b0; font-size: 9px; border: none;")
        col.addWidget(t)
        col.addWidget(s)
        hl.addLayout(col)
        hl.addStretch()

        tm = QLabel(time)
        tm.setStyleSheet("color: #405070; font-size: 9px; border: none;")
        hl.addWidget(tm)
        return frame

    def set_route_info(self, route: dict):
        """Update the route info bar with real OSRM distance + arrival time."""
        from datetime import datetime, timedelta
        self._route_values["dest"].setText(route.get("dest_name", "HAL東京"))
        self._route_values["dist"].setText(f"{route['distance_km']} km")
        eta = datetime.now() + timedelta(minutes=route["duration_min"])
        self._route_values["eta"].setText(eta.strftime("%H:%M"))
        self.show_nav_status("")   # clear status once route is shown

    def _emit_search(self):
        q = self.search_input.text().strip()
        if q:
            self.search_requested.emit(q)
            self.search_input.clear()

    def show_nav_status(self, text: str):
        """Show search/route feedback under the search box."""
        if text:
            self.nav_status_label.setText(text)
            self.nav_status_label.setVisible(True)
        else:
            self.nav_status_label.setVisible(False)

    def _set_as_location(self):
        """Geocode the text in the search box and save as home location."""
        q = self.search_input.text().strip()
        if not q:
            self.show_nav_status("📍 検索欄に現在地の名前を入力してね")
            return
        self.show_nav_status(f"📍 「{q}」を検索中...")
        self._loc_geo.search(q)

    def _on_location_found(self, result: dict):
        lat, lon, city = result["lat"], result["lon"], result["name"]
        save_location(lat, lon, city)
        self._loc_label.setText(f"📍 現在地: {city}")
        self.show_nav_status(f"✅ 現在地を「{city}」に設定したよ！")
        self.search_input.clear()
        if self.is_real_map:
            self.map_widget.set_location(lat, lon)
        self.location_set.emit(lat, lon, city)
