import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QRadialGradient
from config import NEON_BLUE, NEON_GREEN, NEON_ORANGE, NEON_RED


class SpeedGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed = 0
        self.max_speed = 200
        self.setMinimumSize(200, 200)

    def set_speed(self, speed: int):
        self.speed = speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 10

        grad = QRadialGradient(cx, cy, r)
        grad.setColorAt(0, QColor(10, 20, 50))
        grad.setColorAt(1, QColor(5, 10, 25))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(20, 40, 80), 2))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        painter.setPen(QPen(QColor(20, 40, 80), 8, Qt.SolidLine, Qt.RoundCap))
        start_angle, span_angle = 225 * 16, -270 * 16
        painter.drawArc(cx - r + 10, cy - r + 10, (r - 10) * 2, (r - 10) * 2, start_angle, span_angle)

        ratio = min(self.speed / self.max_speed, 1.0)
        if ratio > 0:
            arc_color = NEON_BLUE if ratio < 0.5 else (NEON_ORANGE if ratio < 0.75 else NEON_RED)
            painter.setPen(QPen(arc_color, 8, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(cx - r + 10, cy - r + 10, (r - 10) * 2, (r - 10) * 2,
                            start_angle, int(span_angle * ratio))

        for i in range(0, 201, 20):
            angle_rad = math.radians(225 - (270 * i / 200))
            is_major = (i % 40 == 0)
            inner = r - (18 if is_major else 12)
            outer = r - 4
            x1 = cx + inner * math.cos(angle_rad)
            y1 = cy - inner * math.sin(angle_rad)
            x2 = cx + outer * math.cos(angle_rad)
            y2 = cy - outer * math.sin(angle_rad)
            painter.setPen(QPen(QColor(100, 150, 220) if is_major else QColor(40, 60, 100),
                                2 if is_major else 1))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            if is_major:
                lx = cx + (inner - 14) * math.cos(angle_rad)
                ly = cy - (inner - 14) * math.sin(angle_rad)
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.setPen(QPen(QColor(120, 160, 220)))
                painter.drawText(int(lx) - 10, int(ly) - 6, 20, 12, Qt.AlignCenter, str(i))

        angle_rad = math.radians(225 - (270 * self.speed / self.max_speed))
        nx = cx + (r - 25) * math.cos(angle_rad)
        ny = cy - (r - 25) * math.sin(angle_rad)
        painter.setPen(QPen(NEON_BLUE, 2))
        painter.drawLine(cx, cy, int(nx), int(ny))

        painter.setBrush(QBrush(NEON_BLUE))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - 5, cy - 5, 10, 10)

        painter.setFont(QFont("Segoe UI", 26, QFont.Bold))
        painter.setPen(QPen(QColor(220, 240, 255)))
        painter.drawText(0, cy + 10, w, 40, Qt.AlignCenter, str(self.speed))
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QPen(QColor(100, 140, 200)))
        painter.drawText(0, cy + 42, w, 20, Qt.AlignCenter, "km/h")
        painter.end()


class RiskGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.risk = 0
        self.setMinimumSize(160, 160)
        self.setMaximumSize(160, 160)

    def set_risk(self, risk: int):
        self.risk = risk
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 8

        grad = QRadialGradient(cx, cy, r)
        grad.setColorAt(0, QColor(15, 10, 30))
        grad.setColorAt(1, QColor(8, 5, 15))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(40, 20, 60), 2))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        painter.setPen(QPen(QColor(30, 15, 50), 7, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(cx - r + 8, cy - r + 8, (r - 8) * 2, (r - 8) * 2, 225 * 16, -270 * 16)

        ratio = min(self.risk / 100, 1.0)
        if ratio > 0:
            color = NEON_GREEN if ratio < 0.5 else (NEON_ORANGE if ratio < 0.7 else NEON_RED)
            painter.setPen(QPen(color, 7, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(cx - r + 8, cy - r + 8, (r - 8) * 2, (r - 8) * 2,
                            225 * 16, int(-270 * 16 * ratio))

        color = NEON_GREEN if self.risk < 50 else (NEON_ORANGE if self.risk < 70 else NEON_RED)
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        painter.setPen(QPen(color))
        painter.drawText(0, cy - 15, w, 30, Qt.AlignCenter, f"{self.risk}%")
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QPen(QColor(150, 120, 180)))
        painter.drawText(0, cy + 12, w, 18, Qt.AlignCenter, "事故リスク")
        painter.end()
