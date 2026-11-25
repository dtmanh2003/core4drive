"""
Continuous background wake-word listener.
Runs in a QThread, silently listens for "Hey Neuro" variants.
Emits wake_detected() when triggered.
Call stop() before quitting the app.
"""
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False

# Accepted wake-word phrases (lowercase match)
WAKE_WORDS = [
    "hey neuro", "neuro", "ニューロ", "ヘイニューロ",
    "ねえニューロ", "ねえ、ニューロ",
]


class WakeWordListener(QThread):
    wake_detected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        if _SR_AVAILABLE:
            self._rec = sr.Recognizer()
            self._rec.energy_threshold         = 350
            self._rec.dynamic_energy_threshold  = True
            self._rec.pause_threshold           = 0.6

    @property
    def is_available(self) -> bool:
        return _SR_AVAILABLE

    def start_listening(self):
        if not _SR_AVAILABLE or self.isRunning():
            return
        self._active = True
        self.start()

    def stop(self):
        self._active = False

    def run(self):
        while self._active:
            try:
                with sr.Microphone() as source:
                    self._rec.adjust_for_ambient_noise(source, duration=0.3)
                    audio = self._rec.listen(source, timeout=3, phrase_time_limit=4)

                text = self._rec.recognize_google(audio, language="ja-JP").lower()
                if any(w in text for w in WAKE_WORDS):
                    self.wake_detected.emit()

            except sr.WaitTimeoutError:
                pass        # silence — keep looping
            except sr.UnknownValueError:
                pass        # noise / unclear — keep looping
            except Exception:
                pass        # network / mic error — keep looping
