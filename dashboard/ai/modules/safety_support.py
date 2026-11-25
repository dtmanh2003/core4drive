"""
Module 7 — 安全運転支援 (Safety Support)
Speed Warning / Driver Fatigue Alert / Rest Recommendation
/ Dangerous Area Warning / Driving Advice
"""
import random
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


SPEED_WARN_KMH   = 100
SPEED_DANGER_KMH = 130
RISK_WARN_PCT    = 60
RISK_DANGER_PCT  = 80
FATIGUE_MIN      = 90    # minutes of continuous driving before fatigue alert
REST_COOLDOWN_MIN = 30   # don't repeat rest suggestion within X minutes

# Sudden speed-change detection (per 1-second frame)
ACCEL_SPIKE_KMH  = 15    # +15 km/h in 1s → sudden acceleration (急加速)
BRAKE_SPIKE_KMH  = 15    # -15 km/h in 1s → hard braking (急ブレーキ)

_DANGER_ZONES = [
    {"name": "交差点付近",     "risk_add": 10},
    {"name": "学校ゾーン",     "risk_add": 15},
    {"name": "工事区間",       "risk_add": 20},
    {"name": "カーブ多発地帯", "risk_add": 12},
]

_DRIVING_TIPS = [
    "前の車との車間距離は「3秒ルール」で保とう。",
    "交差点では必ず左右確認！",
    "雨の日はブレーキ距離が1.5倍になるよ。",
    "高速道路では追い越し後すぐに左車線に戻ってね。",
    "疲れを感じたらすぐ休憩！眠気は最大の敵だよ。",
    "スマホ操作は絶対ダメ！ボイスコントロールを使ってね。",
]


class SafetySupport(QObject):
    """
    Safety monitoring system.
    Emits:
      safety_alert(str, str)   — (level: "warn"|"danger", message)
    """
    safety_alert = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drive_start    = datetime.now()
        self._last_rest_warn = datetime.min
        self._last_spd_warn  = 0       # epoch seconds
        self._last_risk_warn = 0
        self._last_accel_warn = 0      # for sudden speed-change alerts
        self._prev_speed     = None    # previous frame speed (for delta)
        self._fatigue_alerted = False
        self._in_danger_zone  = False

        # Fatigue check every 5 minutes
        self._fatigue_timer = QTimer(self)
        self._fatigue_timer.timeout.connect(self._check_fatigue)
        self._fatigue_timer.start(300_000)

        # Random danger zone every 3 minutes (simulated)
        self._zone_timer = QTimer(self)
        self._zone_timer.timeout.connect(self._simulate_danger_zone)
        self._zone_timer.start(180_000)

    # ── State update ──────────────────────────────────────────────────────────
    def update(self, speed: int, risk: int):
        now = int(datetime.now().timestamp())

        # ── Sudden speed change (急加速 / 急ブレーキ) — spoken aloud ──────────
        if self._prev_speed is not None and now - self._last_accel_warn > 5:
            delta = speed - self._prev_speed
            if delta >= ACCEL_SPIKE_KMH:
                self._last_accel_warn = now
                self.safety_alert.emit(
                    "danger",
                    f"急加速を検知！+{delta}km/h。落ち着いて運転してね！"
                )
            elif delta <= -BRAKE_SPIKE_KMH:
                self._last_accel_warn = now
                self.safety_alert.emit(
                    "danger",
                    f"急ブレーキを検知！{delta}km/h。車間距離に注意して！"
                )
        self._prev_speed = speed

        # Speed warning — cooldown 90s warn / 60s danger to avoid spam
        if speed >= SPEED_DANGER_KMH and now - self._last_spd_warn > 60:
            self._last_spd_warn = now
            self.safety_alert.emit(
                "danger",
                f"⚠ {speed}km/h！かなり速いよ。すぐ落としてね！"
            )
        elif speed >= SPEED_WARN_KMH and now - self._last_spd_warn > 90:
            self._last_spd_warn = now
            self.safety_alert.emit(
                "warn",
                f"速度{speed}km/h。制限速度を超えてない？確認してね。"
            )

        # Risk warning — cooldown 90s warn / 60s danger
        if risk >= RISK_DANGER_PCT and now - self._last_risk_warn > 60:
            self._last_risk_warn = now
            self.safety_alert.emit(
                "danger",
                f"事故リスク{risk}%！前方に危険！すぐに速度を落として！"
            )
        elif risk >= RISK_WARN_PCT and now - self._last_risk_warn > 90:
            self._last_risk_warn = now
            self.safety_alert.emit(
                "warn",
                f"リスク{risk}%。前の車との距離を取ってね。"
            )

    # ── Fatigue check ─────────────────────────────────────────────────────────
    def _check_fatigue(self):
        driven_min = int((datetime.now() - self._drive_start).total_seconds() / 60)
        if driven_min >= FATIGUE_MIN and not self._fatigue_alerted:
            self._fatigue_alerted = True
            self.safety_alert.emit(
                "warn",
                f"連続運転{driven_min}分だよ。そろそろ休憩してね！"
            )

    def reset_fatigue(self):
        self._drive_start     = datetime.now()
        self._fatigue_alerted = False

    # ── Danger zone simulation ────────────────────────────────────────────────
    def _simulate_danger_zone(self):
        zone = random.choice(_DANGER_ZONES)
        self.safety_alert.emit(
            "warn",
            f"前方に{zone['name']}があるよ。速度を落として注意！"
        )

    # ── Query responses ───────────────────────────────────────────────────────
    def fatigue_reply(self) -> str:
        driven = int((datetime.now() - self._drive_start).total_seconds() / 60)
        if driven >= FATIGUE_MIN:
            return f"もう{driven}分も運転してるよ！休憩を取るべきだよ。"
        remaining = FATIGUE_MIN - driven
        return f"{driven}分運転中。あと{remaining}分したら休憩を検討してね。"

    def rest_reply(self) -> str:
        return "近くにSAやコンビニを探すよ！5分の休憩でも全然違うよ。"

    @staticmethod
    def driving_advice() -> str:
        return random.choice(_DRIVING_TIPS)

    def speed_warning_reply(self, speed: int) -> str:
        if speed >= SPEED_DANGER_KMH:
            return f"{speed}km/h！危険だよ、今すぐ速度を落として！"
        if speed >= SPEED_WARN_KMH:
            return f"{speed}km/hは少し速いかな。安全速度内に抑えてね。"
        return f"{speed}km/h。安全な速度だよ！このまま行こう。"

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        driven = int((datetime.now() - self._drive_start).total_seconds() / 60)
        fatigue = "yes" if driven >= FATIGUE_MIN else f"no ({driven} min driven)"
        return (
            f"Drive time: {driven} min | Fatigue risk: {fatigue}\n"
            f"Speed threshold: {SPEED_WARN_KMH}/{SPEED_DANGER_KMH} km/h | "
            f"Risk threshold: {RISK_WARN_PCT}/{RISK_DANGER_PCT}%"
        )
