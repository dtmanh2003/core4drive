from datetime import datetime
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(44)
        self.setStyleSheet("background: #07101e; border-bottom: 1px solid #1a2a4a; border-radius: 0px;")

        hl = QHBoxLayout(self)
        hl.setContentsMargins(16, 0, 16, 0)

        app_name = QLabel("⬡ CORE-4 DRIVE")
        app_name.setFont(QFont("Segoe UI", 12, QFont.Bold))
        app_name.setStyleSheet("color: #00aaff; letter-spacing: 3px; border: none;")
        hl.addWidget(app_name)

        sub = QLabel("  AI ASSISTANT - NEURO")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #405080; border: none;")
        hl.addWidget(sub)

        hl.addStretch()

        self.time_label = QLabel()
        self.time_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.time_label.setStyleSheet("color: #e0e8ff; border: none;")
        hl.addWidget(self.time_label)

        self.weather_label = QLabel("  ☀ 24°C")
        self.weather_label.setStyleSheet("color: #80a0d0; font-size: 11px; border: none;")
        hl.addWidget(self.weather_label)

        hl.addStretch()

        self.load_btn = QPushButton("📂 Load CSV")
        self.load_btn.setStyleSheet(
            "background: #0a1e3a; color: #40aaff; border: 1px solid #1a4a80; "
            "border-radius: 6px; padding: 3px 10px; font-size: 10px; font-weight: bold;"
        )
        self.load_btn.setToolTip("データファイル (CSV) を読み込む")
        hl.addWidget(self.load_btn)

        self.data_status = QLabel("データ未読込")
        self.data_status.setStyleSheet("color: #304060; font-size: 9px; border: none; padding: 0 6px;")
        hl.addWidget(self.data_status)

        for icon, color in [("WiFi", "#00aaff"), ("BT", "#8060ff"), ("🎙", "#00ff8c"), ("⚙", "#405080")]:
            btn = QPushButton(icon)
            btn.setStyleSheet(
                f"color: {color}; background: transparent; border: none; font-size: 11px; padding: 2px 6px;"
            )
            hl.addWidget(btn)

        self._clock = QTimer()
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)
        self._tick()

    def _tick(self):
        self.time_label.setText(datetime.now().strftime("%H:%M"))

    # Weather icon by Japanese condition keyword
    _WX_ICON = {"晴れ": "☀", "くもり": "☁", "曇": "☁", "小雨": "🌧",
                "雨": "🌧", "雪": "❄", "晴れ時々": "🌤"}

    def update_weather(self, cond: str, temp):
        icon = "☀"
        for key, ic in self._WX_ICON.items():
            if key in cond:
                icon = ic
                break
        self.weather_label.setText(f"  {icon} {temp}°C")
        self.weather_label.setToolTip(cond)


class BottomBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(50)
        self.setStyleSheet("background: #07101e; border-top: 1px solid #1a2a4a; border-radius: 0px;")

        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)

        tabs = [
            ("🏠", "ホーム"), ("🗺", "ナビ"), ("🎵", "メディア"),
            ("⊕ AI", "AIアシスタント"), ("🚗", "車両設定"), ("⚙", "設定"),
        ]
        for i, (icon, name) in enumerate(tabs):
            btn = QPushButton(f"{icon}\n{name}")
            style = "background: transparent; color: #4060a0; border: none; font-size: 9px; padding: 4px 0px;"
            if i == 3:
                style += " color: #00aaff; border-top: 2px solid #00aaff;"
            btn.setStyleSheet(style)
            btn.setMinimumWidth(70)
            hl.addWidget(btn)
