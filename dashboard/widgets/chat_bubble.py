from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QTimer

# Max bubble text width (px). Wrapping happens within this.
BUBBLE_MAX_W = 290


class WrapLabel(QLabel):
    """
    A word-wrapping QLabel that always reports the correct height for its
    wrapped content — fixes the classic 'last line cut off' bug where a
    plain QLabel computes height for a single line.
    """
    def __init__(self, text: str, max_width: int = BUBBLE_MAX_W, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setMaximumWidth(max_width)
        # Height depends on width → tell the layout to honor heightForWidth
        sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Lock minimum height to the wrapped height at the current width
        self.setMinimumHeight(self.heightForWidth(self.width()))


class ChatBubble(QFrame):
    """Normal chat message bubble."""

    def __init__(self, text: str, sender: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if sender == "user":
            name = QLabel("あなた")
            name.setStyleSheet("color: #6080c0; font-size: 9px; border: none;")
            name.setAlignment(Qt.AlignRight)
            layout.addWidget(name)

            msg = WrapLabel(text)
            msg.setStyleSheet(
                "background: #1a2a5a; color: #d0e0ff; border-radius: 10px; "
                "padding: 8px 12px; font-size: 12px; border: 1px solid #2a3a7a;"
            )
            msg.setAlignment(Qt.AlignLeft)
            layout.addWidget(msg, alignment=Qt.AlignRight)
        else:
            name = QLabel("⊕ Neuro")
            name.setStyleSheet("color: #00aaff; font-size: 9px; font-weight: bold; border: none;")
            layout.addWidget(name)

            msg = WrapLabel(text)
            msg.setStyleSheet(
                "background: #0d1f3a; color: #a0c8ff; border-radius: 10px; "
                "padding: 8px 12px; font-size: 12px; border: 1px solid #1a3a6a;"
            )
            layout.addWidget(msg, alignment=Qt.AlignLeft)

        self.setStyleSheet("border: none; background: transparent;")


class TypingBubble(QFrame):
    """
    Animated 3-dot typing indicator inside the chat.
    Shown while STT is listening / AI is thinking.
    Call stop() before removing from layout.
    """

    # Each frame: dots cycling — uses plain ASCII-safe chars for max compatibility
    _FRAMES_USER  = ["●  ○  ○", "●  ●  ○", "○  ●  ●", "○  ○  ●", "○  ●  ○"]
    _FRAMES_NEURO = ["•  ·  ·", "·  •  ·", "·  ·  •", "·  •  •", "•  •  ·"]

    def __init__(self, sender: str = "user", label: str = "", parent=None):
        super().__init__(parent)
        self._sender = sender
        self._step   = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        if sender == "user":
            name = QLabel("あなた")
            name.setStyleSheet("color: #6080c0; font-size: 9px; border: none;")
            name.setAlignment(Qt.AlignRight)
            layout.addWidget(name)

            self.dots = QLabel(label or self._FRAMES_USER[0])
            self.dots.setMaximumWidth(160)
            self.dots.setStyleSheet(
                "background: #1a2a5a; color: #8090d0; border-radius: 10px; "
                "padding: 8px 18px; font-size: 15px; border: 1px solid #2a3a7a; "
                "letter-spacing: 3px;"
            )
            self.dots.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.dots, alignment=Qt.AlignRight)
        else:
            name = QLabel("⊕ Neuro")
            name.setStyleSheet("color: #00aaff; font-size: 9px; font-weight: bold; border: none;")
            layout.addWidget(name)

            self.dots = QLabel(label or self._FRAMES_NEURO[0])
            self.dots.setMaximumWidth(140)
            self.dots.setStyleSheet(
                "background: #0d1f3a; color: #406090; border-radius: 10px; "
                "padding: 8px 18px; font-size: 14px; border: 1px solid #1a3a6a; "
                "letter-spacing: 3px;"
            )
            self.dots.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.dots, alignment=Qt.AlignLeft)

        self.setStyleSheet("border: none; background: transparent;")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(350)

    def _tick(self):
        frames = self._FRAMES_USER if self._sender == "user" else self._FRAMES_NEURO
        self._step = (self._step + 1) % len(frames)
        self.dots.setText(frames[self._step])

    def set_text(self, text: str):
        """Freeze the bubble with recognized text (stop animation, show text)."""
        self.stop()
        self.dots.setText(text)
        if self._sender == "user":
            self.dots.setStyleSheet(
                "background: #1a2a5a; color: #d0e0ff; border-radius: 10px; "
                "padding: 8px 12px; font-size: 12px; border: 1px solid #2a3a7a;"
            )
            self.dots.setMaximumWidth(280)
            self.dots.setWordWrap(True)
        else:
            self.dots.setStyleSheet(
                "background: #0d1f3a; color: #a0c8ff; border-radius: 10px; "
                "padding: 8px 12px; font-size: 12px; border: 1px solid #1a3a6a;"
            )
            self.dots.setMaximumWidth(300)
            self.dots.setWordWrap(True)

    def stop(self):
        self._timer.stop()
