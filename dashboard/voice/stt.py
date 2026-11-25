"""
Speech-to-Text worker (QThread).
Listens from microphone once, converts to text via Google STT.
Signals:
  listening()         — mic is active, recording started
  recognized(str)     — speech converted to text
  error(str)          — "TIMEOUT" | "UNRECOGNIZED" | "NO_MIC" | "API_ERROR:..." | "ERROR:..."
"""
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False


class SpeechToText(QThread):
    listening    = pyqtSignal()
    recognized   = pyqtSignal(str)
    error        = pyqtSignal(str)

    def __init__(self, language: str = "ja-JP", parent=None):
        super().__init__(parent)
        self.language = language
        self._available = _SR_AVAILABLE
        if _SR_AVAILABLE:
            self._rec = sr.Recognizer()
            self._rec.energy_threshold        = 300
            self._rec.dynamic_energy_threshold = True
            self._rec.pause_threshold          = 0.8

    @property
    def is_available(self) -> bool:
        return self._available

    def run(self):
        if not self._available:
            self.error.emit("NO_MIC")
            return
        try:
            with sr.Microphone() as source:
                self._rec.adjust_for_ambient_noise(source, duration=0.4)
                self.listening.emit()
                audio = self._rec.listen(source, timeout=8, phrase_time_limit=12)

            text = self._rec.recognize_google(audio, language=self.language).strip()

            # Filter: ignore empty or suspiciously short results (likely noise)
            if len(text) < 2:
                self.error.emit("UNRECOGNIZED")
                return

            self.recognized.emit(text)

        except sr.WaitTimeoutError:
            self.error.emit("TIMEOUT")
        except sr.UnknownValueError:
            self.error.emit("UNRECOGNIZED")
        except sr.RequestError as e:
            self.error.emit(f"API_ERROR:{e}")
        except Exception as e:
            self.error.emit(f"ERROR:{e}")
