"""
Module 5 — 車両サポート (Vehicle Support)
Speed Check / Engine Status / Fuel Status / Battery Status / Maintenance Reminder
"""
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


# ── Thresholds ────────────────────────────────────────────────────────────────
FUEL_WARN    = 20    # %
BATTERY_WARN = 15    # %
OIL_WARN_KM  = 500   # km until next oil change


class VehicleSupport(QObject):
    """
    Real-time vehicle state monitor.
    Emits maintenance_alert(str) for passive warnings.
    """
    maintenance_alert = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Simulated vehicle state (replace with OBD-II reader later)
        self.speed:     int   = 0
        self.risk:      int   = 0
        self.fuel:      int   = 65      # %
        self.battery:   int   = 85      # %
        self.engine:    str   = "正常"
        self.seatbelt:  bool  = True
        self.door_lock: bool  = True
        self.mileage:   int   = 42_350  # km
        self.oil_last:  int   = 42_000  # km at last oil change
        self._alerted: set    = set()

        # Check maintenance every 5 minutes
        self._maint_timer = QTimer(self)
        self._maint_timer.timeout.connect(self._check_maintenance)
        self._maint_timer.start(300_000)
        self._check_maintenance()

    # ── State update ──────────────────────────────────────────────────────────
    def update(self, speed: int, risk: int):
        self.speed = speed
        self.risk  = risk

    def update_real(self, speed: int, risk: int, battery_pct: int | None = None):
        """Overwrite with live telemetry from the real car (services/car_link.py)."""
        self.speed = speed
        self.risk  = risk
        if battery_pct is not None:
            self.battery = battery_pct

    # ── Maintenance check ─────────────────────────────────────────────────────
    def _check_maintenance(self):
        km_since_oil = self.mileage - self.oil_last
        if km_since_oil >= OIL_WARN_KM and "oil" not in self._alerted:
            self._alerted.add("oil")
            self.maintenance_alert.emit(
                f"オイル交換の時期が近いよ！（前回交換から{km_since_oil}km走行）"
            )
        if self.fuel <= FUEL_WARN and "fuel" not in self._alerted:
            self._alerted.add("fuel")
            self.maintenance_alert.emit(f"燃料残量{self.fuel}%。そろそろ給油してね！")
        if self.battery <= BATTERY_WARN and "battery" not in self._alerted:
            self._alerted.add("battery")
            self.maintenance_alert.emit(f"バッテリー{self.battery}%。充電を検討してね。")

    def reset_alert(self, key: str):
        self._alerted.discard(key)

    # ── Query responses ───────────────────────────────────────────────────────
    def speed_reply(self) -> str:
        spd = self.speed
        if spd == 0:   return "今は停車中だよ。"
        if spd < 60:   note = "ゆっくり走ってるね。"
        elif spd < 100: note = "いいペースだよ！"
        elif spd < 130: note = "ちょっと速いかな。"
        else:           note = "飛ばしすぎ！気をつけて！"
        return f"今{spd}km/hだよ。{note}"

    def engine_reply(self) -> str:
        return f"エンジン状態：{self.engine}。問題なく動いてるよ！"

    def fuel_reply(self) -> str:
        f = self.fuel
        if f <= FUEL_WARN:
            return f"燃料{f}%！そろそろ給油しないとやばいよ。"
        if f <= 40:
            return f"燃料{f}%。余裕はあるけど念のため確認してね。"
        return f"燃料{f}%。まだ全然大丈夫！"

    def battery_reply(self) -> str:
        b = self.battery
        if b <= BATTERY_WARN:
            return f"バッテリー{b}%。早めに充電してね！"
        return f"バッテリー{b}%。良好だよ。"

    def full_status_reply(self) -> str:
        seatbelt = "装着" if self.seatbelt else "未装着"
        door     = "施錠" if self.door_lock else "未施錠"
        return (
            f"エンジン{self.engine}、燃料{self.fuel}%、"
            f"バッテリー{self.battery}%、"
            f"シートベルト{seatbelt}、ドア{door}。全部OK！"
        )

    def maintenance_reply(self) -> str:
        km = self.mileage - self.oil_last
        items = []
        if km >= OIL_WARN_KM - 100:
            items.append(f"オイル交換 ({km}km経過)")
        if self.fuel <= FUEL_WARN + 10:
            items.append(f"給油 (残{self.fuel}%)")
        if not items:
            return "メンテナンスは特に問題なし！そのまま走れるよ。"
        return "要確認：" + "、".join(items)

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        return (
            f"Speed: {self.speed} km/h | Engine: {self.engine} | "
            f"Fuel: {self.fuel}% | Battery: {self.battery}% | "
            f"Mileage: {self.mileage} km | Seatbelt: {self.seatbelt}"
        )
