from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from config import NEON_BLUE, NEON_ORANGE, NEON_RED


class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self._anim_offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._anim_offset = (self._anim_offset + 1) % 30
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        painter.fillRect(0, 0, w, h, QColor(8, 14, 30))

        painter.setPen(QPen(QColor(15, 30, 55), 1))
        for x in range(0, w, 30):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, 30):
            painter.drawLine(0, y, w, y)

        road_pen = QPen(QColor(25, 50, 90), 14, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(road_pen)
        path = QPainterPath()
        path.moveTo(w * 0.1, h * 0.8)
        path.cubicTo(w * 0.3, h * 0.6, w * 0.5, h * 0.5, w * 0.7, h * 0.3)
        path.lineTo(w * 0.9, h * 0.15)
        painter.drawPath(path)

        route_pen = QPen(QColor(0, 120, 255, 180), 4, Qt.DashLine)
        route_pen.setDashOffset(self._anim_offset)
        painter.setPen(route_pen)
        painter.drawPath(path)

        dx, dy = int(w * 0.88), int(h * 0.13)
        painter.setBrush(QBrush(NEON_BLUE))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        dest_path = QPainterPath()
        dest_path.moveTo(dx, dy + 14)
        dest_path.arcTo(dx - 7, dy - 14, 14, 18, 0, 180)
        dest_path.closeSubpath()
        painter.drawPath(dest_path)
        painter.setFont(QFont("Segoe UI", 6, QFont.Bold))
        painter.setPen(QPen(Qt.white))
        painter.drawText(dx - 20, dy - 26, 40, 12, Qt.AlignCenter, "HAL東京")

        cx_car = int(w * 0.28)
        cy_car = int(h * 0.62)
        pulse_r = 12 + (self._anim_offset % 10)
        painter.setBrush(QBrush(QColor(0, 170, 255, 40)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx_car - pulse_r, cy_car - pulse_r, pulse_r * 2, pulse_r * 2)
        painter.setBrush(QBrush(NEON_BLUE))
        painter.setPen(QPen(Qt.white, 1))
        painter.drawEllipse(cx_car - 8, cy_car - 8, 16, 16)
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.setPen(QPen(Qt.white))
        painter.drawText(cx_car - 6, cy_car - 6, 12, 12, Qt.AlignCenter, "▲")

        for rx, ry, icon, color in [
            (0.6, 0.4, "⚠", NEON_RED),
            (0.5, 0.52, "!", NEON_ORANGE),
            (0.38, 0.63, "≡", QColor(255, 200, 0)),
        ]:
            mx, my = int(w * rx), int(ry * h)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(mx - 9, my - 9, 18, 18)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(QPen(Qt.white))
            painter.drawText(mx - 6, my - 6, 12, 12, Qt.AlignCenter, icon)

        painter.end()
