"""
CenterPanel — AI chat UI.
Talks only to NeuroCore; no direct module access.
"""
import random
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from config import PANEL_STYLE
from ai.neuro_core import NeuroCore
from widgets.chat_bubble import ChatBubble, TypingBubble


class CenterPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_state       = "idle"
        self._user_typing:  TypingBubble | None = None   # user STT indicator
        self._neuro_typing: TypingBubble | None = None   # Neuro thinking indicator

        # ── NeuroCore (single interface to all 9 modules) ─────────────────────
        self.core = NeuroCore(self)
        self.core.response_ready.connect(self._on_response)
        self.core.proactive_alert.connect(self._on_alert)
        self.core.tts_speak.connect(self.core.voice.speak)

        self.setStyleSheet(PANEL_STYLE)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # Header
        hdr = QLabel("AI ASSISTANT - NEURO")
        hdr.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hdr.setStyleSheet("color: #00aaff; letter-spacing: 2px; border: none;")
        hdr.setAlignment(Qt.AlignCenter)
        layout.addWidget(hdr)

        # Status row
        status_row = QHBoxLayout()
        self.state_label = QLabel("● Ready")
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet(
            "color: #00aaff; font-size: 10px; background: #051020; "
            "border: 1px solid #0a3060; border-radius: 6px; padding: 3px 10px;"
        )
        status_row.addWidget(self.state_label, stretch=1)

        self.mic_toggle = QPushButton("🎤")
        self.mic_toggle.setFixedSize(30, 24)
        self.mic_toggle.setCheckable(True)
        self.mic_toggle.setToolTip("常時ウェイクワード監視 ON/OFF")
        self.mic_toggle.setStyleSheet(self._toggle_style("#404060", False))
        self.mic_toggle.toggled.connect(self._on_mic_toggle)
        status_row.addWidget(self.mic_toggle)

        self.tts_btn = QPushButton("🔊")
        self.tts_btn.setFixedSize(30, 24)
        self.tts_btn.setCheckable(True)
        self.tts_btn.setChecked(True)
        self.tts_btn.setToolTip("音声読み上げ ON/OFF")
        self.tts_btn.setStyleSheet(self._toggle_style("#40aaff", True))
        self.tts_btn.toggled.connect(self._on_tts_toggle)
        status_row.addWidget(self.tts_btn)
        layout.addLayout(status_row)

        # Suggestion box
        sug_frame = QFrame()
        sug_frame.setStyleSheet("background: #0a1530; border: 1px solid #1a3060; border-radius: 8px;")
        sl = QVBoxLayout(sug_frame)
        sl.setContentsMargins(10, 6, 10, 6)
        sl.setSpacing(3)
        QLabel("⭐ Neuro Suggestion", sug_frame).setStyleSheet(
            "color: #8060ff; font-size: 9px; font-weight: bold; border: none;"
        )
        sl.addWidget(sug_frame.findChildren(QLabel)[0])
        self.suggest_label = QLabel("いつもの目的地、HAL東京まで案内しますか？")
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setStyleSheet("color: #b0a0ff; font-size: 10px; border: none;")
        sl.addWidget(self.suggest_label)
        layout.addWidget(sug_frame)

        # Chat scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: 1px solid #1a2a4a; border-radius: 8px; background: #07101e; }"
        )
        chat_container = QWidget()
        chat_container.setStyleSheet("background: #07101e;")
        self.chat_layout = QVBoxLayout(chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()
        self.scroll_area.setWidget(chat_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # API key row (collapsible)
        self.api_row = QFrame()
        self.api_row.setStyleSheet("border: none; background: transparent;")
        al = QHBoxLayout(self.api_row)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Anthropic API key → Enter")
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setStyleSheet(
            "background: #0d1530; color: #c0d8ff; border: 1px solid #3050a0; "
            "border-radius: 6px; padding: 6px 10px; font-size: 10px;"
        )
        self.api_input.returnPressed.connect(self._save_api_key)
        al.addWidget(self.api_input)
        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(48)
        save_btn.setStyleSheet(
            "background: #1a3060; color: #80c0ff; border: 1px solid #2050a0; "
            "border-radius: 6px; padding: 6px; font-size: 10px; font-weight: bold;"
        )
        save_btn.clicked.connect(self._save_api_key)
        al.addWidget(save_btn)
        self.api_row.setVisible(False)
        layout.addWidget(self.api_row)

        # Input row
        input_frame = QFrame()
        input_frame.setStyleSheet("border: none; background: transparent;")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(6)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Neuroに話しかけてください...")
        self.text_input.setStyleSheet(
            "background: #0a1525; color: #d0e0ff; border: 1px solid #1a3060; "
            "border-radius: 8px; padding: 8px 12px; font-size: 11px;"
        )
        self.text_input.returnPressed.connect(self.send_message)
        il.addWidget(self.text_input)

        send_btn = QPushButton("送信")
        send_btn.setFixedWidth(52)
        send_btn.setStyleSheet(
            "background: #003880; color: #80c8ff; border: 1px solid #0060cc; "
            "border-radius: 8px; padding: 8px 0; font-weight: bold; font-size: 11px;"
        )
        send_btn.clicked.connect(self.send_message)
        il.addWidget(send_btn)

        self.key_btn = QPushButton("🔑")
        self.key_btn.setFixedWidth(34)
        self.key_btn.setStyleSheet(
            "background: #12102a; color: #6050c0; border: 1px solid #2a2060; "
            "border-radius: 8px; padding: 8px 0; font-size: 14px;"
        )
        self.key_btn.clicked.connect(lambda: self.api_row.setVisible(
            not self.api_row.isVisible()
        ))
        il.addWidget(self.key_btn)
        layout.addWidget(input_frame)

        # Hey Neuro button
        self.mic_btn = QPushButton("🎙  Hey Neuro")
        self.mic_btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.mic_btn.setMinimumHeight(54)
        self.mic_btn.setStyleSheet(self._mic_style(False))
        self.mic_btn.clicked.connect(self.activate_voice)
        layout.addWidget(self.mic_btn)

        self.hint_label = QLabel()
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: #405080; font-size: 9px; border: none;")
        layout.addWidget(self.hint_label)


        # Animation
        self.wave_timer = QTimer()
        self.wave_timer.timeout.connect(self._anim_tick)
        self.wave_step = 0
        self.wave_chars = [
            "◉ Listening ▁▂▃▄", "◉ Listening ▂▃▄▅",
            "◉ Listening ▃▄▅▄", "◉ Listening ▄▅▄▃", "◉ Listening ▅▄▃▂",
        ]

        # Update suggestion every 30 s
        self._sug_timer = QTimer(self)
        self._sug_timer.timeout.connect(self._refresh_suggestion)
        self._sug_timer.start(30_000)

        # Neuro proactively talks (chat bubble + voice) to feel like a companion
        self._last_proactive = ""
        self._proactive_timer = QTimer(self)
        self._proactive_timer.timeout.connect(self._proactive_talk)
        self._proactive_timer.start(75_000)   # every 75s when idle

        # Wire TTS state
        self.core.voice.tts.started_speaking.connect(lambda: self._set_state("speaking"))
        self.core.voice.tts.finished_speaking.connect(lambda: self._set_state("idle"))

        # ── Voice pipeline → UI ───────────────────────────────────────────────
        # When STT recognizes speech: show user bubble + go to "thinking"
        self.core.voice.speech_recognized.connect(self._on_voice_recognized)
        # When STT fails: reset UI + show error
        self.core.voice.stt_error.connect(self._on_stt_error_ui)

        # Initial greeting
        self._update_hint()
        greeting = self.core.learning.personalized_greeting()
        self._add_neuro(greeting)

    # ── Style helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _mic_style(active: bool) -> str:
        if active:
            return ("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    "stop:0 #3a0080,stop:1 #004080);"
                    "color:#ff80a0;border:2px solid #ff2060;border-radius:27px;font-size:14px;")
        return ("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #1a0050,stop:1 #002060);"
                "color:#a080ff;border:2px solid #5020c0;border-radius:27px;font-size:14px;")

    @staticmethod
    def _toggle_style(color: str, on: bool) -> str:
        bg = "#0a1a30" if on else "#12102a"
        border = color if on else "#303050"
        return (f"background:{bg};color:{color if on else '#404060'};"
                f"border:1px solid {border};border-radius:4px;font-size:13px;")

    # ── Chat helpers ──────────────────────────────────────────────────────────
    def _add_neuro(self, text: str):
        self._remove_neuro_typing()
        bubble = ChatBubble(text, "neuro")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._scroll_bottom()

    def _add_user(self, text: str):
        # Remove the listening/typing indicator, then add a proper bubble
        self._remove_user_typing()
        bubble = ChatBubble(text, "user")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._scroll_bottom()

    def _start_user_typing(self):
        """Insert animated typing bubble for the user (while STT is recording)."""
        self._user_typing = TypingBubble("user", parent=self.scroll_area.widget())
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._user_typing)
        self._scroll_bottom()

    def _start_neuro_typing(self):
        """Insert animated typing bubble for Neuro (while AI is thinking)."""
        self._neuro_typing = TypingBubble("neuro", parent=self.scroll_area.widget())
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._neuro_typing)
        self._scroll_bottom()

    def _remove_user_typing(self):
        if self._user_typing:
            self._user_typing.stop()
            self._user_typing.setParent(None)
            self._user_typing.deleteLater()
            self._user_typing = None

    def _remove_neuro_typing(self):
        if self._neuro_typing:
            self._neuro_typing.stop()
            self._neuro_typing.setParent(None)
            self._neuro_typing.deleteLater()
            self._neuro_typing = None

    def _scroll_bottom(self):
        QTimer.singleShot(80, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    # ── State machine ─────────────────────────────────────────────────────────
    def _anim_tick(self):
        self.wave_step = (self.wave_step + 1) % len(self.wave_chars)
        if self.ai_state == "listening":
            self.state_label.setText(self.wave_chars[self.wave_step])
            self.state_label.setStyleSheet(
                "color:#ff6040;font-size:10px;background:#1a0800;"
                "border:1px solid #a03000;border-radius:6px;padding:3px 10px;"
            )
        elif self.ai_state == "thinking":
            dots = "." * ((self.wave_step % 3) + 1)
            self.state_label.setText(f"◌ Thinking{dots}")
            self.state_label.setStyleSheet(
                "color:#ffcc00;font-size:10px;background:#1a1400;"
                "border:1px solid #a08000;border-radius:6px;padding:3px 10px;"
            )
        elif self.ai_state == "speaking":
            bars = ["♪ Speaking ▂▅▇▅▂", "♪ Speaking ▅▇▅▂▅", "♪ Speaking ▇▅▂▅▇"]
            self.state_label.setText(bars[self.wave_step % 3])
            self.state_label.setStyleSheet(
                "color:#00ff8c;font-size:10px;background:#001a0d;"
                "border:1px solid #00a060;border-radius:6px;padding:3px 10px;"
            )

    def _set_state(self, state: str):
        self.ai_state = state
        if state == "idle":
            self.wave_timer.stop()
            self.state_label.setText("● Ready")
            self.state_label.setStyleSheet(
                "color:#00aaff;font-size:10px;background:#051020;"
                "border:1px solid #0a3060;border-radius:6px;padding:3px 10px;"
            )
            self.mic_btn.setStyleSheet(self._mic_style(False))
            self.mic_btn.setText("🎙  Hey Neuro")
        else:
            if not self.wave_timer.isActive():
                self.wave_timer.start(300)

    # ── Voice recognition handlers ────────────────────────────────────────────
    def _on_voice_recognized(self, text: str):
        """STT recognized → setup UI first, THEN call handle()."""
        # 1. Setup UI (must happen before handle() to avoid stuck bubble)
        self._add_user(text)           # freeze user typing bubble → real text
        self._start_neuro_typing()     # Neuro thinking bubble
        self._set_state("thinking")
        # 2. Now send to AI (response_ready may fire synchronously)
        self.core.handle(text)

    def _on_stt_error_ui(self, error: str):
        """STT failed → remove typing bubble → show error → reset."""
        self._remove_user_typing()
        self._reset_mic_btn()
        self._set_state("idle")
        msgs = {
            "TIMEOUT":      "聞こえなかったよ。もう一回話しかけてね！",
            "UNRECOGNIZED": "うまく聞き取れなかった。もう一度お願い！",
            "NO_MIC":       "マイクが使えないよ。テキストで入力してね。",
        }
        self._add_neuro(msgs.get(error, "音声エラーが発生したよ。テキストで試してね。"))
        self.text_input.setFocus()

    def _reset_mic_btn(self):
        self.mic_btn.setStyleSheet(self._mic_style(False))
        self.mic_btn.setText("🎙  Hey Neuro")

    # ── Voice activation ──────────────────────────────────────────────────────
    def activate_voice(self):
        if self.ai_state != "idle":
            return
        if self.core.voice.stt_available:
            self._set_state("listening")
            self.mic_btn.setStyleSheet(self._mic_style(True))
            self.mic_btn.setText("🔴  Listening...")
            self._start_user_typing()          # show ● ○ ○ bubble in chat
            self.core.listen_once()
        else:
            self._add_neuro(random.choice(["はい！何？", "呼んだ？", "何か手伝える？"]))
            self.text_input.setFocus()

    def _on_mic_toggle(self, checked: bool):
        self.mic_toggle.setStyleSheet(
            self._toggle_style("#40ff60", checked) if checked
            else self._toggle_style("#404060", False)
        )
        if checked:
            self.core.voice.start_wake_listening()
        else:
            self.core.voice.stop_wake_listening()

    def _on_tts_toggle(self, checked: bool):
        self.tts_btn.setStyleSheet(self._toggle_style("#40aaff", checked))
        self.core.user.set_pref("tts_enabled", checked)

    # ── Send message ──────────────────────────────────────────────────────────
    def send_message(self):
        text = self.text_input.text().strip()
        if not text or self.ai_state != "idle":
            return
        self.text_input.clear()
        self._add_user(text)           # normal bubble (no voice)
        self._start_neuro_typing()     # show ▁▂▃ while waiting for AI
        self._set_state("thinking")
        self.core.handle(text)

    # ── Receive response ──────────────────────────────────────────────────────
    def _on_response(self, text: str):
        self._add_neuro(text)
        self._reset_mic_btn()
        self._update_mode_badge()
        if self.tts_btn.isChecked() and self.core.voice.tts_available:
            self._set_state("speaking")
        else:
            self._set_state("idle")

    def _update_mode_badge(self):
        """Show which AI engine answered."""
        mode   = getattr(self.core, "_current_mode", "offline")
        ollama = getattr(self.core, "ollama", None)
        if mode == "online":
            self.hint_label.setText("☁ Online — Claude AI")
            self.hint_label.setStyleSheet("color: #3080a0; font-size: 9px; border: none;")
        elif ollama and getattr(ollama, "_avail", False):
            self.hint_label.setText(f"🦙 Offline — {ollama.MODEL} (Ollama)")
            self.hint_label.setStyleSheet("color: #306050; font-size: 9px; border: none;")
        else:
            self.hint_label.setText("🔌 Offline — ルールベース")
            self.hint_label.setStyleSheet("color: #505030; font-size: 9px; border: none;")

    def _on_alert(self, level: str, message: str):
        # Only show alerts when truly idle — never interrupt conversation
        if self.ai_state != "idle":
            return
        # Only show danger alerts in chat to avoid spam
        # "info" level alerts (ETA, route) are silently ignored in chat
        if level == "danger":
            self._add_neuro(f"⚠ {message}")
        elif level == "warn":
            self._add_neuro(message)

    # ── API key ───────────────────────────────────────────────────────────────
    def _save_api_key(self):
        key = self.api_input.text().strip()
        if not key:
            return
        self.core.configure_ai(key)
        self.api_input.clear()
        self.api_row.setVisible(False)
        self.key_btn.setStyleSheet(
            "background:#0a2a10;color:#40c060;border:1px solid #206030;"
            "border-radius:8px;padding:8px 0;font-size:14px;"
        )
        self._add_neuro("APIキー設定完了！Claude AIで全力サポートするね！")
        self._update_hint()

    def _update_hint(self):
        if self.core.is_ai_configured:
            self.hint_label.setText("Claude AI • 9モジュール統合")
            self.hint_label.setStyleSheet("color:#306050;font-size:9px;border:none;")
        else:
            self.hint_label.setText("🔑 APIキー未設定 — ローカルモードで動作中")
            self.hint_label.setStyleSheet("color:#604020;font-size:9px;border:none;")

    # ── Periodic suggestion refresh ───────────────────────────────────────────
    def _refresh_suggestion(self):
        rsk = self.core.vehicle.risk
        s = self.core.learning.smart_suggestion(risk=rsk) or \
            self.core.user.suggestion(risk=rsk)
        self.suggest_label.setText(s)

    def _proactive_talk(self):
        """Neuro proactively speaks up (chat + voice) so it feels like a friend."""
        # Only when idle (don't interrupt) and not while listening/speaking
        if self.ai_state != "idle":
            return

        spd = self.core.vehicle.speed
        rsk = self.core.vehicle.risk

        # Context-aware proactive line (e.g. lunch question) takes priority
        ctx_line = self.core.proactive_line()
        if ctx_line:
            self._last_proactive = ctx_line
            self._add_neuro(ctx_line)
            if self.tts_btn.isChecked() and self.core.voice.tts_available:
                self.core.voice.speak(ctx_line)
            return

        # High risk → always a safety nudge
        if rsk >= 70:
            msg = self.core.user.suggestion(risk=rsk)
        else:
            # Mix habit suggestion with casual chit-chat for variety
            chit_chat = [
                "順調だね！この調子でいこう。",
                "何か必要なら声かけてね。",
                "ドライブ日和だね〜。",
                "音楽でもかける？気分転換にいいよ。",
                "ちょっと一息どう？無理は禁物だよ。",
                "今日も安全運転、ありがとう！",
            ]
            if spd == 0:
                chit_chat.append("信号待ちかな？焦らずいこう。")
            options = [self.core.learning.smart_suggestion(risk=rsk) or
                       self.core.user.suggestion(risk=rsk)] + chit_chat
            msg = random.choice(options)

        if not msg or msg == self._last_proactive:
            return   # don't repeat the same line back to back
        self._last_proactive = msg
        self._add_neuro(msg)                 # show as a Neuro chat bubble
        if self.tts_btn.isChecked() and self.core.voice.tts_available:
            self.core.voice.speak(msg)       # speak it aloud

    # ── Dashboard update (called from MainWindow every second) ────────────────
    def update_data(self, speed: int, risk: int):
        self.core.update_vehicle(speed, risk)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def closeEvent(self, event):
        self.core.voice.stop_speaking()
        self.core.voice.stop_wake_listening()
        self.core.learning.end_session()
        super().closeEvent(event)
