"""
Text-to-Speech worker (QThread).
Speaks Japanese via pyttsx3 (offline, Windows SAPI5).

IMPORTANT (Windows): the SAPI5 COM engine must be created AND used in the
SAME thread, with COM initialized for that thread. So we build a fresh engine
inside run() (the QThread), not in __init__. Creating it on the main thread and
calling runAndWait() from the worker thread = silent failure.

Signals:
  started_speaking()
  finished_speaking()
"""
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False


def _find_japanese_voice(engine):
    for v in engine.getProperty("voices"):
        name = (v.name or "").lower()
        vid  = (v.id  or "").lower()
        if "ja-jp" in vid or "japan" in name or "haruka" in name or "ichiro" in name or "sayaka" in name:
            return v.id
    return None


def _check_available() -> bool:
    """One-time check that pyttsx3 initializes (don't keep the engine)."""
    if not _TTS_AVAILABLE:
        return False
    try:
        e = pyttsx3.init()
        ok = e.getProperty("voices") is not None
        try:
            e.stop()
        except Exception:
            pass
        return ok
    except Exception:
        return False


class TextToSpeech(QThread):
    started_speaking  = pyqtSignal()
    finished_speaking = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._available = _check_available()
        self.rate   = 178
        self.volume = 0.95

    @property
    def is_available(self) -> bool:
        return self._available

    def speak(self, text: str):
        """Queue text and start speaking (non-blocking)."""
        if not self._available or self.isRunning() or not text:
            return
        self._text = text
        self.start()

    def run(self):
        text = self._text
        if not text:
            self.finished_speaking.emit()
            return

        # Initialize COM for THIS thread (Windows SAPI5 requirement)
        com_ready = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            com_ready = True
        except Exception:
            pass

        try:
            self.started_speaking.emit()
            engine = pyttsx3.init()                 # fresh engine in this thread
            ja = _find_japanese_voice(engine)
            if ja:
                engine.setProperty("voice", ja)
            engine.setProperty("rate",   self.rate)
            engine.setProperty("volume", self.volume)
            engine.say(text)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
        except Exception:
            pass
        finally:
            if com_ready:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
            self.finished_speaking.emit()
