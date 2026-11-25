from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from config import PANEL_STYLE
from widgets.gauges import SpeedGauge, RiskGauge


class LeftPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(PANEL_STYLE)
        self.setMinimumWidth(260)
        self.setMaximumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QLabel("車両状態")
        header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        header.setStyleSheet("color: #00aaff; letter-spacing: 2px; border: none;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.speed_gauge = SpeedGauge()
        layout.addWidget(self.speed_gauge, alignment=Qt.AlignCenter)

        cruise = QLabel("⚡ CRUISE")
        cruise.setAlignment(Qt.AlignCenter)
        cruise.setStyleSheet("color: #00aaff; font-size: 10px; font-weight: bold; border: none;")
        layout.addWidget(cruise)

        self.status_label = QLabel("● SAFE")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.status_label.setStyleSheet(
            "color: #00ff8c; background: #001a0d; border: 1px solid #00ff8c; "
            "border-radius: 8px; padding: 4px 12px;"
        )
        layout.addWidget(self.status_label)

        self.risk_gauge = RiskGauge()
        layout.addWidget(self.risk_gauge, alignment=Qt.AlignCenter)

        self.risk_desc = QLabel("安全な状態です\n快適にドライブ中")
        self.risk_desc.setAlignment(Qt.AlignCenter)
        self.risk_desc.setStyleSheet("color: #aaaacc; font-size: 9px; border: none;")
        layout.addWidget(self.risk_desc)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #1a2a4a; max-height: 1px; border: none;")
        layout.addWidget(line)

        engine_title = QLabel("エンジン状態")
        engine_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        engine_title.setStyleSheet("color: #7080aa; border: none;")
        layout.addWidget(engine_title)

        self.engine_label = QLabel("⚙  正常  NORMAL")
        self.engine_label.setStyleSheet("color: #00ff8c; font-size: 10px; border: none;")
        layout.addWidget(self.engine_label)

        layout.addWidget(self._stat_row(
            "燃料残量", "65%", "⛽", "#00aaff",
            "バッテリー", "85%", "🔋", "#00ff8c"
        ))
        layout.addWidget(self._stat_row(
            "シートベルト", "装着済み", "🔒", "#00ff8c",
            "ドアロック", "施錠済み", "🚪", "#00aaff"
        ))
        layout.addStretch()

    def _stat_row(self, l1, v1, i1, c1, l2, v2, i2, c2):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        for label, val, icon, color in [(l1, v1, i1, c1), (l2, v2, i2, c2)]:
            box = QFrame()
            box.setStyleSheet("background: #0a1525; border: 1px solid #1a2a4a; border-radius: 6px;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(6, 4, 6, 4)
            bl.setSpacing(1)
            QLabel(f"{icon} {label}", box).setStyleSheet("color: #6070a0; font-size: 8px; border: none;")
            v = QLabel(val, box)
            v.setFont(QFont("Segoe UI", 9, QFont.Bold))
            v.setStyleSheet(f"color: {color}; border: none;")
            bl.addWidget(box.findChildren(QLabel)[0])
            bl.addWidget(v)
            hl.addWidget(box)
        return row

    def update_status(self, speed: int, risk: int):
        self.speed_gauge.set_speed(speed)
        self.risk_gauge.set_risk(risk)

        if risk >= 70 or speed >= 130:
            status, color, bg = "● DANGER", "#ff2828", "#1a0000"
            desc = "危険！速度を落として\n安全確認してください"
        elif risk >= 50 or speed >= 100:
            status, color, bg = "● WARNING", "#ff8c00", "#1a0a00"
            desc = "前方車両との\n距離が近いです"
        else:
            status, color, bg = "● SAFE", "#00ff8c", "#001a0d"
            desc = "安全な状態です\n快適にドライブ中"

        self.risk_desc.setText(desc)
        self.status_label.setText(status)
        self.status_label.setStyleSheet(
            f"color: {color}; background: {bg}; border: 1px solid {color}; "
            "border-radius: 8px; padding: 4px 12px; font-size: 11px; font-weight: bold;"
        )
