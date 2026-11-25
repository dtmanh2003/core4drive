import sys
import random
import os

# ── QtWebEngine init — MUST run before QApplication is created ─────────────────
# Required for the real OSM map (widgets/map_view.py) to render correctly.
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa: F401 (early import)
except Exception:
    pass

from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFileDialog
from PyQt5.QtCore import QTimer

from config import STYLE_MAIN
from data_loader import DataLoader, speed_to_risk
from widgets.left_panel import LeftPanel
from widgets.center_panel import CenterPanel
from widgets.right_panel import RightPanel
from widgets.bars import TopBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Core-4 Drive — AI Assistant Neuro")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 780)
        self.setStyleSheet(STYLE_MAIN)

        self.data_loader = DataLoader()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        panels = QWidget()
        panels.setStyleSheet("background: #09111f;")
        panels_layout = QHBoxLayout(panels)
        panels_layout.setContentsMargins(10, 10, 10, 10)
        panels_layout.setSpacing(10)

        self.left_panel   = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel  = RightPanel()

        panels_layout.addWidget(self.left_panel,   stretch=3)
        panels_layout.addWidget(self.center_panel, stretch=4)
        panels_layout.addWidget(self.right_panel,  stretch=4)
        root.addWidget(panels, stretch=1)

        self.top_bar.load_btn.clicked.connect(self.load_data_file)
        self._auto_load_csv()

        # TopBar weather + real map location/route: update when real data arrives
        try:
            wx = self.center_panel.core.info.get_weather()
            self.top_bar.update_weather(wx.get("cond", "晴れ"), wx.get("temp", 24))
            self.center_panel.core.weather_updated.connect(self._on_weather_data)
            self.center_panel.core.route_updated.connect(self._on_route_data)
            # Google-Maps-like search: panel search box → geocode + route
            self.right_panel.search_requested.connect(self.center_panel.core.navigate_to)
            self.center_panel.core.nav_status.connect(self.right_panel.show_nav_status)
            # Location button: re-fetch weather when user sets a new home location
            self.right_panel.location_set.connect(self._on_location_set)
            # Real car (smart_ai_car_servo): move the map marker as it drives
            self.center_panel.core.car_position_updated.connect(self._on_car_position)
        except Exception:
            pass

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_dashboard)
        self.update_timer.start(1000)
        self.update_dashboard()

    def closeEvent(self, event):
        try:
            self.center_panel.core.car.stop_polling()
            self.center_panel.core.car.wait(1000)
        except Exception:
            pass
        super().closeEvent(event)

    def _on_location_set(self, lat: float, lon: float, city: str):
        """User set a new home location → re-fetch weather for that location."""
        self.center_panel.core.refresh_weather()

    def _on_weather_data(self, data: dict):
        """Real weather/location arrived → update TopBar + center the map."""
        self.top_bar.update_weather(data["cond"], data["temp"])
        if getattr(self.right_panel, "is_real_map", False) and "lat" in data:
            self.right_panel.map_widget.set_location(data["lat"], data["lon"])

    def _on_car_position(self, lat: float, lon: float):
        """Real car moved (dead-reckoned from wheel speed) → move the marker."""
        if getattr(self.right_panel, "is_real_map", False):
            self.right_panel.map_widget.update_car(lat, lon)

    def _on_route_data(self, route: dict):
        """Real OSRM route ready → draw it on the map + update route info bar."""
        if getattr(self.right_panel, "is_real_map", False):
            self.right_panel.map_widget.draw_route(
                route["coords"], route["dest_lat"], route["dest_lon"], route["dest_name"]
            )
        # Update the route info bar (distance + ETA) if the panel exposes it
        self.right_panel.set_route_info(route)

    # ── Data file ─────────────────────────────────────────────────────────────
    def _auto_load_csv(self):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [f for f in os.listdir(project_dir) if f.lower().endswith(".csv")]
        if not candidates:
            return
        preferred = [f for f in candidates if any(
            kw in f.lower() for kw in ("speed", "data", "sensor", "obd", "real", "log", "drive")
        )]
        target = preferred[0] if preferred else candidates[0]
        ok, msg = self.data_loader.load_csv(os.path.join(project_dir, target))
        self._apply_load_result(ok, msg)

    def load_data_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "データファイルを選択 (CSV)",
            os.path.dirname(os.path.abspath(__file__)),
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self._apply_load_result(*self.data_loader.load_csv(path))

    def _apply_load_result(self, ok: bool, msg: str):
        if ok:
            self.top_bar.load_btn.setStyleSheet(
                "background: #0a2e1a; color: #40ff80; border: 1px solid #1a8040; "
                "border-radius: 6px; padding: 3px 10px; font-size: 10px; font-weight: bold;"
            )
            self.top_bar.data_status.setStyleSheet(
                "color: #40aa60; font-size: 9px; border: none; padding: 0 6px;"
            )
            self.top_bar.data_status.setText(f"✓ {self.data_loader.file_name}")
        else:
            self.top_bar.data_status.setStyleSheet(
                "color: #aa4040; font-size: 9px; border: none; padding: 0 6px;"
            )
            self.top_bar.data_status.setText(f"✗ {msg}")

    # ── Dashboard update ──────────────────────────────────────────────────────
    def update_dashboard(self):
        if self.data_loader.loaded:
            speed = self.data_loader.next_speed()
            risk  = speed_to_risk(speed)
            cur, total = self.data_loader.progress
            loop = " ↺" if self.data_loader.looped else ""
            self.top_bar.data_status.setText(
                f"✓ {self.data_loader.file_name}  {cur}/{total}{loop}"
            )
        else:
            speed = random.randint(40, 140)
            risk  = random.randint(20, 85)

        self.left_panel.update_status(speed, risk)
        self.center_panel.update_data(speed, risk)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Core-4 Drive")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
