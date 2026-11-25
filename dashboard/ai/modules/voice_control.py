"""
Module 1 — 音声制御 (Voice Control)
Coordinates: Wake Word / Speech Recognition / Voice Command / TTS
"""
from PyQt5.QtCore import QObject, pyqtSignal
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.wake_word import WakeWordListener

# ── Intent keyword map ─────────────────────────────────────────────────────────
# Maps recognized text patterns → intent strings used by NeuroCore
VOICE_INTENTS = {
    "navigation":  ["ナビ", "案内", "目的地", "帰る", "行き方", "道"],
    "music_play":  ["音楽", "再生", "曲をかけて", "music", "play"],
    "music_stop":  ["止めて", "音楽やめて", "stop", "pause", "ポーズ"],
    "music_next":  ["次の曲", "スキップ", "next", "変えて"],
    "weather":     ["天気", "気温", "weather", "雨", "晴れ"],
    "speed_check": ["速度", "スピード", "何キロ", "speed"],
    "fuel_check":  ["燃料", "ガソリン", "fuel"],
    "battery":     ["バッテリー", "battery", "充電"],
    "engine":      ["エンジン", "engine"],
    "time":        ["何時", "時間", "今何時"],
    "reminder":    ["メモ", "リマインダー", "覚えておいて", "reminder"],
    "rest":        ["休憩", "疲れた", "眠い", "rest"],
    "emergency":   ["緊急", "助けて", "sos", "emergency"],
    "volume_up":   ["音量上げて", "ボリューム上げ", "volume up"],
    "volume_down": ["音量下げて", "ボリューム下げ", "volume down"],
    "eta":         ["あと何分", "到着", "eta", "いつ着く"],
}


def detect_intent(text: str) -> str | None:
    """Return intent string or None if no match."""
    tl = text.lower()
    for intent, keywords in VOICE_INTENTS.items():
        if any(k in tl for k in keywords):
            return intent
    return None


class VoiceControl(QObject):
    """
    Facade that wires STT / TTS / WakeWord together.
    Emits:
      speech_recognized(str)  — STT succeeded
      stt_error(str)          — STT failed
      wake_detected()         — wake word heard
    """
    speech_recognized = pyqtSignal(str)
    stt_error         = pyqtSignal(str)
    wake_detected     = pyqtSignal()

    def __init__(self, language: str = "ja-JP", parent=None):
        super().__init__(parent)
        self._lang = language

        self.stt       = SpeechToText(language=language, parent=self)
        self.tts       = TextToSpeech(parent=self)
        self.wake_word = WakeWordListener(parent=self)

        self.stt.recognized.connect(self.speech_recognized)
        self.stt.error.connect(self.stt_error)
        self.wake_word.wake_detected.connect(self.wake_detected)

    # ── STT ───────────────────────────────────────────────────────────────────
    @property
    def stt_available(self) -> bool:
        return self.stt.is_available

    def listen_once(self):
        """Start one-shot STT recording."""
        if not self.stt.isRunning():
            self.stt.start()

    # ── TTS ───────────────────────────────────────────────────────────────────
    @property
    def tts_available(self) -> bool:
        return self.tts.is_available

    def speak(self, text: str):
        self.tts.speak(text)

    def stop_speaking(self):
        if self.tts.isRunning():
            self.tts.terminate()

    # ── Wake word ─────────────────────────────────────────────────────────────
    def start_wake_listening(self):
        self.wake_word.start_listening()

    def stop_wake_listening(self):
        self.wake_word.stop()
        if self.wake_word.isRunning():
            self.wake_word.wait(1500)

    # ── Intent ────────────────────────────────────────────────────────────────
    @staticmethod
    def get_intent(text: str) -> str | None:
        return detect_intent(text)

    # ── Status for prompt ─────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        return (
            f"Voice input: {'available' if self.stt_available else 'unavailable'}\n"
            f"Voice output: {'available' if self.tts_available else 'unavailable'}"
        )
