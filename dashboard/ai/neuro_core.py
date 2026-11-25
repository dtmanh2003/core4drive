"""
NeuroCore — Central orchestrator for all 9 Neuro AI modules.

Architecture:
  NeuroCore
  ├── Module 1: VoiceControl        (voice_control.py)
  ├── Module 2: ConversationMemory  (conversation.py)
  ├── Module 3: UserManagement      (user_management.py)
  ├── Module 4: Information         (information.py)
  ├── Module 5: VehicleSupport      (vehicle_support.py)
  ├── Module 6: Navigation          (navigation.py)
  ├── Module 7: SafetySupport       (safety_support.py)
  ├── Module 8: MediaControl        (media_control.py)
  └── Module 9: LearningSystem      (learning_system.py)

CenterPanel talks only to NeuroCore.
NeuroCore routes to the right module or Claude API.
"""
from PyQt5.QtCore import QObject, pyqtSignal

from ai.neuro_agent   import NeuroAgent
from ai.neuro_ai      import NeuroAI
from ai.ollama_agent  import OllamaAgent
from ai.modules.voice_control   import VoiceControl
from ai.modules.conversation    import ConversationMemory
from ai.modules.user_management import UserManagement
from ai.modules.information     import Information
from ai.modules.vehicle_support import VehicleSupport
from ai.modules.navigation      import Navigation
from ai.modules.safety_support  import SafetySupport
from ai.modules.media_control   import MediaControl
from ai.modules.learning_system import LearningSystem


class NeuroCore(QObject):
    """
    Single interface for CenterPanel.
    Signals:
      response_ready(str)       — text reply for chat bubble
      proactive_alert(str, str) — (level, message) from modules
      tts_speak(str)            — text to speak aloud
    """
    response_ready  = pyqtSignal(str)
    proactive_alert = pyqtSignal(str, str)   # level, message
    tts_speak       = pyqtSignal(str)
    weather_updated = pyqtSignal(dict)       # real weather arrived
    route_updated   = pyqtSignal(dict)       # real OSRM route ready
    nav_status      = pyqtSignal(str)        # search/route status for UI
    car_position_updated = pyqtSignal(float, float)  # dead-reckoned real car position

    # Real coords of the usual destination (HAL東京, Shinjuku)
    _DEST_COORDS = {"HAL東京": (35.6916, 139.6953)}

    # Distance between the real car's left/right wheels (meters).
    # Used to turn differential wheel speed into a heading change for
    # dead-reckoning (the car has no GPS). Tune to match the real chassis
    # if the marker drifts noticeably faster/slower than the car turns.
    _WHEEL_BASE_M = 0.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode     = "offline"  # "offline" | "online"
        self._offline_fallback = ""

        # ── Instantiate all 9 modules ─────────────────────────────────────────
        self.voice   = VoiceControl(parent=self)      # Module 1
        self.memory  = ConversationMemory()            # Module 2
        self.user    = UserManagement()                # Module 3
        self.info    = Information()                   # Module 4
        self.vehicle = VehicleSupport(parent=self)     # Module 5
        self.navi    = Navigation(parent=self)         # Module 6
        self.safety  = SafetySupport(parent=self)      # Module 7
        self.media   = MediaControl(                   # Module 8
            preferred_genre=self.user.get_pref("music_genre", "Lo-fi")
        )
        self.learning = LearningSystem()               # Module 9

        # ── Real weather (Open-Meteo + IP geolocation, no key) ───────────────
        from services.weather import WeatherService
        self.weather = WeatherService(self)
        self.weather.weather_ready.connect(self._on_weather)
        self.weather.start()   # fetch in background; falls back if offline

        # ── Real routing (OSRM, no key) ──────────────────────────────────────
        from services.routing import RouteService
        self.routing = RouteService(self)
        self.routing.route_ready.connect(self._on_route)
        self._car_pos: tuple | None = None   # (lat, lon) of the car, from IP
        self._nav_announce = False           # announce ETA when user-requested
        self._pending = None                 # multi-turn context: None | "food" | ("confirm", place)
        self._awaiting_poi = False           # geocoder is doing a nearby POI search
        self._lunch_asked  = False           # asked about lunch already today

        # ── Geocoding (Nominatim, no key) — search any place ─────────────────
        from services.geocoding import GeocodeService
        self.geocoder = GeocodeService(self)
        self.geocoder.found.connect(self._on_geocoded)
        self.geocoder.not_found.connect(self._on_geocode_failed)

        # ── Real car link (smart_ai_car_servo pi_server) ──────────────────────
        # If unreachable, dashboard just keeps using simulated/CSV data.
        from services.car_link import CarLink
        from config import load_car_url
        self.car = CarLink(load_car_url(), parent=self)
        self.car.status_ready.connect(self._on_car_status)
        self.car.connection_changed.connect(self._on_car_connection)
        self._hazard_state = {"emg": 0, "tilt": 0, "impact": 0, "ir": 0}
        # Dead-reckoning state: no GPS on the real car, so position is
        # estimated from wheel speed + heading, anchored at self._car_pos.
        self._dr = {"x": 0.0, "y": 0.0, "heading": 0.0, "last_ts": None}
        self.car.start()

        # ── Offline AI: Ollama (local LLM) ───────────────────────────────────
        self.ollama = OllamaAgent(self)
        self.ollama.response_ready.connect(self._on_ollama_response)
        self.ollama.error_occurred.connect(self._on_ollama_error)
        self.ollama.warm_up()   # preload model into RAM in background

        # ── Online AI: Claude API ─────────────────────────────────────────────
        self.agent = NeuroAgent(self)
        self.agent.response_ready.connect(self._on_agent_response)
        self.agent.error_occurred.connect(self._on_agent_error)

        # ── Wire proactive signals ────────────────────────────────────────────
        self.vehicle.maintenance_alert.connect(
            lambda msg: self._emit_alert("warn", msg)
        )
        self.safety.safety_alert.connect(self._emit_alert)
        self.navi.route_alert.connect(
            lambda msg: self._emit_alert("info", msg)
        )
        self.navi.eta_update.connect(
            lambda msg: self._emit_alert("info", msg)
        )

        # ── Voice pipeline ────────────────────────────────────────────────────
        # speech_recognized is NOT wired here on purpose.
        # CenterPanel._on_voice_recognized() sets up the typing bubble FIRST,
        # then calls self.core.handle(text). This prevents the "stuck bubble" bug
        # where NeuroCore got the text and emitted response_ready before the
        # typing bubble was even created.
        self.voice.wake_detected.connect(self._on_wake_word)
        self.voice.stt_error.connect(self._on_stt_error)

    # ── Public interface ──────────────────────────────────────────────────────
    def handle(self, text: str):
        """
        Offline-first pipeline (fastest path wins):
          1. Intent router    → instant command answer (speed, music, nav…)
          2. NeuroAI confident → instant simple answer (math, greeting, thanks…)
          3. Ollama qwen3:8b   → local LLM for free chat (if running)
          4. Claude API        → online, only if Ollama unavailable & key set
          5. NeuroAI fallback  → always works
        """
        self.memory.add_user(text)
        self.learning.record_query(text)
        self.user.record_action("query")

        # ── Step 0: Pending conversation context (multi-turn flow) ────────────
        if self._handle_pending(text):
            return

        # ── Step 1: Intent router (instant, no AI) ────────────────────────────
        routed = self._route(text)
        if routed:
            self._deliver(routed, mode="offline")
            return

        # ── Step 2: NeuroAI rule-based — instant for simple cases ─────────────
        rule_resp, confident = NeuroAI.respond(
            text, self.vehicle.speed, self.vehicle.risk, self.user
        )
        if confident:
            self._deliver(rule_resp, mode="offline")
            return

        # Save rule answer as fallback for the LLM paths below
        self._offline_fallback = rule_resp

        # ── Step 3: Offline Ollama (local LLM, no internet) ───────────────────
        if self.ollama.is_available:
            habits = self.user._data.get("habits", {})
            self.ollama.set_context(self._build_full_context())   # RAG-lite
            self.ollama.ask(text, self.vehicle.speed, self.vehicle.risk, habits)
            return   # async → _on_ollama_response

        # ── Step 4: Online Claude (internet + API key) ────────────────────────
        if self.agent.is_configured:
            self._ask_claude(text)
            return   # async → _on_agent_response

        # ── Step 5: Rule-based fallback ───────────────────────────────────────
        self._deliver(rule_resp, mode="offline")

    def listen_once(self):
        """Activate STT for one utterance."""
        self.voice.listen_once()

    def update_vehicle(self, speed: int, risk: int):
        """Called every second from MainWindow (simulated/CSV data)."""
        if self.car.connected:
            return   # real telemetry from _on_car_status() takes priority
        self.vehicle.update(speed, risk)
        self.safety.update(speed, risk)
        self.learning.record_speed(speed, risk)

    @property
    def is_ai_configured(self) -> bool:
        return self.agent.is_configured

    def configure_ai(self, api_key: str):
        self.agent.configure(api_key)
        self.memory.clear()

    # ── Intent routing ────────────────────────────────────────────────────────
    def _route(self, text: str) -> str | None:
        """
        Return a direct response string, or None to let Claude handle it.
        """
        intent = self.voice.get_intent(text)
        t = text.lower()

        # Module 4 — Information
        if intent == "time" or any(k in t for k in ["何時", "時間", "today", "今日"]):
            self.learning.record_action("info_time")
            return self.info.time_reply()

        if intent == "weather" or any(k in t for k in ["天気", "気温", "weather"]):
            self.learning.record_action("info_weather")
            return self.info.weather_reply()

        if any(k in t for k in ["ニュース", "news", "最新情報"]):
            self.learning.record_action("info_news")
            return self.info.news_reply()

        if any(k in t for k in ["予定", "スケジュール", "calendar"]):
            self.learning.record_action("info_calendar")
            return self.info.today_schedule()

        if intent == "reminder" or any(k in t for k in ["メモ", "リマインド", "覚えて"]):
            self.learning.record_action("reminder")
            # Extract what to remember
            for kw in ["メモ", "覚えておいて", "リマインド"]:
                if kw in t:
                    content = t.split(kw, 1)[-1].strip()
                    if content:
                        return self.info.add_reminder(content)
            return self.info.list_reminders()

        # Module 5 — Vehicle Support
        if intent == "speed_check" or any(k in t for k in ["速度", "スピード", "何キロ"]):
            self.learning.record_action("vehicle_speed")
            return self.vehicle.speed_reply()

        if intent == "fuel_check" or any(k in t for k in ["燃料", "ガソリン", "fuel"]):
            self.learning.record_action("vehicle_fuel")
            return self.vehicle.fuel_reply()

        if intent == "battery" or any(k in t for k in ["バッテリー", "battery", "充電"]):
            self.learning.record_action("vehicle_battery")
            return self.vehicle.battery_reply()

        if intent == "engine" or any(k in t for k in ["エンジン", "engine"]):
            self.learning.record_action("vehicle_engine")
            return self.vehicle.engine_reply()

        if any(k in t for k in ["車両状態", "車の状態", "点検"]):
            self.learning.record_action("vehicle_status")
            return self.vehicle.full_status_reply()

        if any(k in t for k in ["メンテナンス", "整備", "maintenance"]):
            self.learning.record_action("maintenance")
            return self.vehicle.maintenance_reply()

        # Real car control (smart_ai_car_servo) — only when the physical car is connected
        if self.car.connected:
            if any(k in t for k in ["前進", "進んで", "go forward"]):
                self.learning.record_action("car_forward")
                self.car.drive(120, 120)
                return "了解、前進するね！"
            if any(k in t for k in ["バックして", "後退", "下がって"]):
                self.learning.record_action("car_backward")
                self.car.drive(-100, -100)
                return "バックするね、気をつけて！"
            if any(k in t for k in ["車を止めて", "ブレーキ", "stop car"]):
                self.learning.record_action("car_stop")
                self.car.stop_car()
                return "停止したよ！"
            if any(k in t for k in ["クラクション", "ホーン", "鳴らして"]):
                self.learning.record_action("car_beep")
                self.car.beep()
                return "ププッ！鳴らしたよ。"

        # Module 6 — Navigation (search ANY place, Google-Maps-like)
        if intent == "navigation" or any(k in t for k in ["ナビ", "案内", "行き方", "帰る", "行きたい", "向か"]):
            self.learning.record_action("navigation")
            place = self._extract_place(text)
            if place:
                # Real geocoding + routing to any place
                self._nav_announce = True
                self.navigate_to(place)
                return f"「{place}」を検索して案内するね！ちょっと待ってね。"
            # No specific place → usual destination
            reply = self.navi.destination_reply(text)
            dest  = self.navi._destination["name"] if self.navi._destination else ""
            if dest:
                self.learning.record_destination(dest)
                self.user.record_visit(dest)
            return reply

        if intent == "eta" or any(k in t for k in ["あと何分", "到着", "いつ着く"]):
            self.learning.record_action("eta_check")
            return self.navi.eta_reply()

        if any(k in t for k in ["現在地", "今どこ", "location"]):
            return self.navi.location_reply()

        # Module 7 — Safety
        if intent == "rest" or any(k in t for k in ["疲れた", "眠い", "休憩", "しんどい"]):
            self.learning.record_action("rest_request")
            self.safety.reset_fatigue()
            return self.safety.rest_reply()

        if any(k in t for k in ["アドバイス", "advice", "コツ", "運転のコツ"]):
            self.learning.record_action("driving_advice")
            return self.safety.driving_advice()

        # Module 8 — Media
        if intent == "music_play" or any(k in t for k in ["音楽", "曲", "再生", "かけて"]):
            self.learning.record_action("music_play")
            if any(k in t for k in ["おすすめ", "提案", "何か", "suggest"]):
                return self.media.suggest_by_mood()
            if any(k in t for k in ["お気に入り", "favorite", "好きな"]):
                return self.media.suggest_favorite()
            for genre in ["Lo-fi", "J-Pop", "Jazz", "Rock", "Acoustic", "Classical"]:
                if genre.lower() in t or genre in t:
                    return self.media.change_genre(genre)
            return self.media.play()

        if intent == "music_stop" or any(k in t for k in ["止めて", "音楽やめて", "stop music"]):
            self.learning.record_action("music_stop")
            return self.media.stop()

        if intent == "music_next" or any(k in t for k in ["次の曲", "スキップ", "next"]):
            self.learning.record_action("music_next")
            return self.media.next_track()

        if any(k in t for k in ["前の曲", "戻して", "previous"]):
            self.learning.record_action("music_prev")
            return self.media.prev_track()

        if intent == "volume_up":
            self.learning.record_action("volume_up")
            return self.media.volume_up()

        if intent == "volume_down":
            self.learning.record_action("volume_down")
            return self.media.volume_down()

        if any(k in t for k in ["今の曲", "何流れてる", "what's playing"]):
            return self.media.status_reply()

        # Only match music "like" when clearly about the current song
        if any(k in t for k in ["この曲いいね", "この曲好き", "お気に入りに追加", "曲をお気に入り"]):
            return self.media.like_current()

        # Module 9 — Learning
        if any(k in t for k in ["学習", "覚えた", "パターン", "成長"]):
            return (
                f"今まで{self.learning._profile['driving_stats']['total_sessions']}回ドライブしたよ。"
                f"パーソナライズレベル：{self.learning.personalization_level}/100！"
            )

        # Emergency (always handled directly)
        if any(k in t for k in ["緊急", "助けて", "sos", "emergency", "事故"]):
            self.learning.record_action("emergency")
            self._emit_alert("danger", "緊急モード起動！安全な場所に停車して！")
            return "緊急連絡先に通知するよ！今すぐ安全な場所に停車してね！"

        # No intent matched — return None so handle() can try Ollama / Claude
        return None

    # ── Claude call ───────────────────────────────────────────────────────────
    def _ask_claude(self, text: str):
        """Called only when agent.is_configured (checked in handle())."""
        self.agent._job = {
            "query":  text,
            "speed":  self.vehicle.speed,
            "risk":   self.vehicle.risk,
            "habits": self.user._data.get("habits", {}),
        }
        self.agent.set_context(self._build_full_context())   # full 9-module context
        self.agent._history = self.memory.for_api()
        self.agent.start()

    def _build_full_context(self) -> str:
        """RAG-lite: compact, relevant context for the LLM (not a data dump)."""
        from datetime import datetime
        hour = datetime.now().hour

        # Proactive hint based on learned habits + time of day
        hint = self.learning.smart_suggestion(
            hour=hour, speed=self.vehicle.speed, risk=self.vehicle.risk
        ) or self.user.suggestion(hour=hour, risk=self.vehicle.risk)

        # Most relevant facts only — keep it short so the small model stays focused
        return "\n".join([
            f"[Vehicle] {self.vehicle.context_for_prompt()}",
            f"[User] driver='{self.user.name}', "
            f"usual_destination='{self.user.frequent_destination}', "
            f"music='{self.user.preferred_music}'",
            f"[Info] {self.info.now_str()}, weather {self.info.get_weather().get('cond','?')}",
            f"[Navigation] {self.navi.context_for_prompt()}",
            f"[Media] {self.media.context_for_prompt()}",
            f"[Learning] personalization {self.learning.personalization_level}/100, "
            f"top_place='{self.learning.top_destination or 'unknown'}'",
            f"[Proactive hint you may weave in if relevant] {hint}",
        ])

    # ── Response delivery ─────────────────────────────────────────────────────
    def _deliver(self, text: str, mode: str = "offline"):
        """
        mode: "offline" | "online"
        Emits response_ready with mode tag so UI can show the indicator.
        """
        self.memory.add_assistant(text)
        self.learning.record_action(f"response_{mode}")
        self._current_mode = mode
        self.response_ready.emit(text)
        if self.user.tts_enabled:
            self.tts_speak.emit(text)

    # ── Weather handler ───────────────────────────────────────────────────────
    def _on_weather(self, data: dict):
        """Real weather arrived → update Information + request initial route."""
        self.info.set_live_weather(data)
        self.weather_updated.emit(data)

        # Remember the car's real position (used for any future routing)
        if "lat" in data:
            self._car_pos = (data["lat"], data["lon"])
            # Initial route to the usual destination
            if not self.routing.isRunning():
                dest_name = self.user.frequent_destination
                d_lat, d_lon = self._DEST_COORDS.get(dest_name, self._DEST_COORDS["HAL東京"])
                self.routing.request(data["lat"], data["lon"], d_lat, d_lon, dest_name)

    def refresh_weather(self):
        """Re-fetch weather (called after user sets a new home location)."""
        if not self.weather.isRunning():
            self.weather.start()

    # ── Navigate to ANY place (Google-Maps-like search) ───────────────────────
    def navigate_to(self, place: str):
        """Geocode a place name, then route to it from the car's position."""
        self.nav_status.emit(f"🔍 「{place}」を検索中...")
        self.geocoder.search(place)

    def _on_geocoded(self, place: dict):
        """Place found. Either a nearby POI (food flow) or a direct destination."""
        if not self._car_pos:
            self._car_pos = (35.6895, 139.6917)   # fallback Tokyo center

        # Nearby POI search (e.g. user said "ラーメン") → ask to confirm
        if self._awaiting_poi:
            self._awaiting_poi = False
            self._pending = ("confirm", place)
            self.nav_status.emit(f"📍 {place['name']} を発見")
            self._deliver(
                f"近くに「{place['name']}」を見つけたよ！そこまで案内する？",
                mode="offline",
            )
            return

        # Direct destination → route now
        self.learning.record_action("search_destination")
        self.learning.record_destination(place["name"])
        o_lat, o_lon = self._car_pos
        self.nav_status.emit(f"📍 {place['name']} までルート計算中...")
        self.routing.request(o_lat, o_lon, place["lat"], place["lon"], place["name"])

    def _on_geocode_failed(self, query: str):
        self._awaiting_poi = False
        self.nav_status.emit(f"❌ 「{query}」が見つかりませんでした")
        self._deliver(f"ごめん、近くに「{query}」が見つからなかった。別のお店はどう？", mode="offline")

    # ── Real car handlers (smart_ai_car_servo) ─────────────────────────────────
    def _on_car_connection(self, connected: bool):
        if connected:
            self._deliver("実車と接続したよ！ここからはリアルタイムのデータを表示するね。", mode="offline")
        else:
            self._deliver("実車との接続が切れた。シミュレーションに戻すね。", mode="offline")

    def _on_car_status(self, data: dict):
        """Real telemetry arrived (~1Hz) from pi_server /api/status."""
        t = data.get("telemetry", {})
        speed_kmh = round(t.get("speed", 0.0) * 3.6, 1)   # m/s → km/h
        dist_cm   = t.get("dist")
        hazard    = any(t.get(k) == 1 for k in ("emg", "tilt", "impact", "ir"))
        risk      = self._risk_from_telemetry(speed_kmh, dist_cm, hazard)
        battery   = t.get("motorBatPct")
        battery   = int(round(battery)) if battery is not None else None

        self.vehicle.update_real(int(speed_kmh), risk, battery)
        self.learning.record_speed(int(speed_kmh), risk)

        # Edge-triggered hazard alerts (avoid spamming every 1s poll)
        for key, label in (("emg", "緊急ボタン"), ("tilt", "傾き"), ("impact", "衝撃"), ("ir", "障害物")):
            state = 1 if t.get(key) == 1 else 0
            if state == 1 and self._hazard_state.get(key) == 0:
                self._emit_alert("danger", f"実車で{label}を検知！確認して！")
            self._hazard_state[key] = state

        self._update_car_position(t)

    def _update_car_position(self, telemetry: dict):
        """Dead-reckon the real car's position from wheel speed (no GPS on
        the robot) and move the map marker. Anchored at self._car_pos
        (set once from IP/weather geolocation)."""
        import time, math
        if self._car_pos is None:
            return

        now = time.time()
        last_ts = self._dr["last_ts"]
        self._dr["last_ts"] = now
        if last_ts is None:
            return   # first sample: nothing to integrate yet
        dt = min(now - last_ts, 2.0)   # clamp in case of a long stall
        if dt <= 0:
            return

        v_left  = telemetry.get("speedL", 0.0) or 0.0
        v_right = telemetry.get("speedR", 0.0) or 0.0
        v       = (v_left + v_right) / 2.0
        omega   = (v_right - v_left) / self._WHEEL_BASE_M

        heading = self._dr["heading"] + omega * dt
        x = self._dr["x"] + v * math.cos(heading) * dt
        y = self._dr["y"] + v * math.sin(heading) * dt
        self._dr.update(x=x, y=y, heading=heading)

        lat0, lon0 = self._car_pos
        dlat = y / 111_320.0
        dlon = x / (111_320.0 * math.cos(math.radians(lat0)))
        self.car_position_updated.emit(lat0 + dlat, lon0 + dlon)

    @staticmethod
    def _risk_from_telemetry(speed_kmh: float, dist_cm, hazard: bool) -> int:
        if hazard:
            return 90
        if dist_cm is not None and dist_cm > 0:
            if dist_cm < 15: return 85
            if dist_cm < 30: return 55
            if dist_cm < 60: return 25
        return max(5, min(60, int(speed_kmh * 2)))

    # ── Multi-turn conversation flow ──────────────────────────────────────────
    def _handle_pending(self, text: str) -> bool:
        """Handle a reply that belongs to an ongoing conversation. Returns True if consumed."""
        t = text.strip()
        if self._pending is None:
            return False

        # Waiting for the user to name a food / place type
        if self._pending == "food":
            self._pending = None
            # User declines
            if any(k in t for k in ["いらない", "いい", "結構", "大丈夫", "後で", "やめ", "no"]):
                self._deliver("そっか！お腹すいたらまた言ってね。", mode="offline")
                return True
            # Treat the message as the food/place keyword → search nearby
            keyword = self._extract_food(t)
            self._awaiting_poi = True
            o_lat, o_lon = self._car_pos or (35.6895, 139.6917)
            self.nav_status.emit(f"🔍 近くの「{keyword}」を検索中...")
            self._deliver(f"いいね！近くの「{keyword}」を探すね、ちょっと待って。", mode="offline")
            self.geocoder.search_nearby(keyword, o_lat, o_lon)
            return True

        # Waiting for yes/no to navigate to a found place
        if isinstance(self._pending, tuple) and self._pending[0] == "confirm":
            place = self._pending[1]
            self._pending = None
            if any(k in t for k in ["はい", "うん", "そう", "お願い", "行く", "yes", "おk", "ok", "case", "頼む"]):
                self.learning.record_action("nav_to_food")
                self.learning.record_destination(place["name"])
                self._nav_announce = True
                o_lat, o_lon = self._car_pos or (35.6895, 139.6917)
                self.routing.request(o_lat, o_lon, place["lat"], place["lon"], place["name"])
                self._deliver(f"よし、「{place['name']}」まで案内するね！", mode="offline")
            else:
                self._deliver("わかった、やめとくね。他に行きたいところある？", mode="offline")
            return True

        return False

    @staticmethod
    def _extract_food(text: str) -> str:
        """Clean a food/place reply into a search keyword."""
        t = text.strip()
        for junk in ["が食べたい", "食べたい", "がいい", "にする", "がいいな", "かな", "を探して", "！", "。", "、"]:
            t = t.replace(junk, "")
        return t.strip() or "レストラン"

    # ── Proactive line (called periodically by the UI) ────────────────────────
    def proactive_line(self) -> str | None:
        """
        Return a proactive message for Neuro to say, or None.
        Sets up multi-turn context (e.g. lunch question) when appropriate.
        """
        from datetime import datetime
        hour = datetime.now().hour

        # Lunch time (11–13h): ask what they want to eat, once
        if 11 <= hour < 14 and not self._lunch_asked and self._pending is None:
            self._lunch_asked = True
            self._pending = "food"
            return "お昼の時間だね！何か食べたいものある？ラーメンとかカフェとか、言ってくれたら近くのお店を探すよ！"

        return None

    @staticmethod
    def _extract_place(text: str) -> str | None:
        """Pull a destination name out of a navigation sentence."""
        t = text.strip()
        # Cut at the first navigation marker; whatever is before it = place
        markers = ["まで案内", "までナビ", "まで", "に行きたい", "へ行きたい",
                   "に行って", "へ行って", "に向かって", "へ向かって",
                   "に案内", "へ案内", "に連れて", "へ連れて", "に行く", "へ行く", "へ", "に"]
        for m in markers:
            if m in t:
                place = t.split(m)[0].strip()
                # Strip leading filler ("今から", "ちょっと"...) and the word ナビ/案内
                for junk in ["今から", "ちょっと", "これから", "ねえ", "おい", "ナビ", "案内"]:
                    place = place.replace(junk, "").strip()
                if 1 <= len(place) <= 30:
                    return place
        return None

    # ── Route handler ─────────────────────────────────────────────────────────
    def _on_route(self, route: dict):
        """Real OSRM route ready → update Navigation + notify UI to draw it."""
        self.navi.set_live_route(route)
        self.route_updated.emit(route)
        # If the user explicitly asked to navigate, announce the real ETA
        if getattr(self, "_nav_announce", False):
            self._nav_announce = False
            self._deliver(
                f"{route['dest_name']}まで距離{route['distance_km']}km、"
                f"約{route['duration_min']}分で到着予定だよ！ルートを表示したよ。",
                mode="offline",
            )

    # ── Ollama handlers ───────────────────────────────────────────────────────
    def _on_ollama_response(self, text: str):
        self._deliver(text, mode="offline")   # local model = offline

    def _on_ollama_error(self, error: str):
        """Ollama failed → try Claude, else rule-based."""
        if error == "NOT_RUNNING":
            self.ollama._avail = False   # mark unavailable for this session
        last = self.memory.last_user_msg() or ""
        if self.agent.is_configured:
            self._ask_claude(last)       # escalate (sets full context)
        else:
            resp, _ = NeuroAI.respond(last, self.vehicle.speed, self.vehicle.risk, self.user)
            self._deliver(resp, mode="offline")

    # ── Claude handlers ───────────────────────────────────────────────────────
    def _on_agent_response(self, text: str):
        self._deliver(text, mode="online")

    def _on_agent_error(self, error: str):
        if error == "AUTH":
            resp = "APIキーが無効みたい。🔑から設定してね。"
        else:
            resp, _ = NeuroAI.respond(
                self.memory.last_user_msg() or "",
                self.vehicle.speed, self.vehicle.risk, self.user
            )
        self._deliver(resp, mode="offline")

    def _emit_alert(self, level: str, message: str):
        self.proactive_alert.emit(level, message)
        if level == "danger" and self.user.tts_enabled:
            self.tts_speak.emit(message)

    # ── Voice handlers ────────────────────────────────────────────────────────
    def _handle_voice_input(self, text: str):
        self.handle(text)

    def _on_wake_word(self):
        greets = ["はい！何？", "呼んだ？", "Neuroここにいるよ！"]
        import random
        self._deliver(random.choice(greets))

    def _on_stt_error(self, error: str):
        # CenterPanel handles UI reset via _on_stt_error_ui.
        # NeuroCore only logs — no response_ready emit to avoid duplicate messages.
        self.learning.record_action(f"stt_error_{error}")
