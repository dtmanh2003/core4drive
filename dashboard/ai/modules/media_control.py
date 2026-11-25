"""
Module 8 — メディア制御 (Media Control)
Music Play / Stop / Volume Control / Playlist Control / Favorite Suggestion
"""
import random
from datetime import datetime


_GENRES = {
    "Lo-fi":    ["Lofi Hip Hop Radio", "ChilledCow Mix", "Late Night Study"],
    "J-Pop":    ["City Pop 80s", "J-Pop Drive Mix", "Summer Hits"],
    "Jazz":     ["Tokyo Jazz Bar", "Smooth Jazz Drive", "Blue Note Collection"],
    "Rock":     ["Classic Rock Highway", "Japanese Rock Hits", "Power Drive Rock"],
    "Acoustic": ["Morning Acoustic", "Chill Guitar", "Unplugged Favorites"],
    "Classical":["Mozart for Driving", "Bach Road Trip", "Piano Concerto"],
}

_ALL_TRACKS = [t for tracks in _GENRES.values() for t in tracks]


class MediaControl:
    """Manages music playback, volume, and playlist."""

    def __init__(self, preferred_genre: str = "Lo-fi"):
        self._is_playing   = False
        self._current:     str  = ""
        self._volume:      int  = 70       # 0–100
        self._playlist:    list = list(_GENRES.get(preferred_genre, _ALL_TRACKS[:3]))
        self._history:     list = []
        self._liked:       list = []
        self._genre        = preferred_genre

    # ── Playback ──────────────────────────────────────────────────────────────
    def play(self, track: str = None) -> str:
        if track:
            self._current = track
        elif not self._current:
            self._current = self._playlist[0] if self._playlist else random.choice(_ALL_TRACKS)
        self._is_playing = True
        self._history.append(self._current)
        return f"「{self._current}」を再生するよ♪"

    def stop(self) -> str:
        if not self._is_playing:
            return "今は再生していないよ。"
        self._is_playing = False
        return "音楽を止めたよ。"

    def next_track(self) -> str:
        idx = (self._playlist.index(self._current) + 1
               if self._current in self._playlist else 0)
        idx = idx % len(self._playlist) if self._playlist else 0
        self._current    = self._playlist[idx] if self._playlist else random.choice(_ALL_TRACKS)
        self._is_playing = True
        self._history.append(self._current)
        return f"次は「{self._current}」にするね！"

    def prev_track(self) -> str:
        if len(self._history) < 2:
            return "前の曲はないよ。"
        self._history.pop()
        self._current    = self._history[-1]
        self._is_playing = True
        return f"「{self._current}」に戻したよ。"

    def like_current(self) -> str:
        if self._current and self._current not in self._liked:
            self._liked.append(self._current)
        return f"「{self._current}」をお気に入りに追加したよ！"

    # ── Volume ────────────────────────────────────────────────────────────────
    def volume_up(self, step: int = 10) -> str:
        self._volume = min(100, self._volume + step)
        return f"音量を{self._volume}%に上げたよ。"

    def volume_down(self, step: int = 10) -> str:
        self._volume = max(0, self._volume - step)
        return f"音量を{self._volume}%に下げたよ。"

    def set_volume(self, level: int) -> str:
        self._volume = max(0, min(100, level))
        return f"音量を{self._volume}%にしたよ。"

    # ── Playlist / Suggestion ─────────────────────────────────────────────────
    def shuffle(self) -> str:
        random.shuffle(self._playlist)
        self._current    = self._playlist[0] if self._playlist else ""
        self._is_playing = True
        return f"シャッフルして「{self._current}」を再生するよ！"

    def suggest_by_mood(self, hour: int = None) -> str:
        h = hour or datetime.now().hour
        if 6 <= h < 10:
            genre, tracks = "Acoustic", _GENRES["Acoustic"]
        elif 10 <= h < 17:
            genre, tracks = "J-Pop", _GENRES["J-Pop"]
        elif 17 <= h < 21:
            genre, tracks = "Lo-fi", _GENRES["Lo-fi"]
        else:
            genre, tracks = "Jazz", _GENRES["Jazz"]
        track = random.choice(tracks)
        return f"今の気分には「{genre}」がいいかも！「{track}」を流そうか？"

    def suggest_favorite(self) -> str:
        if self._liked:
            return f"お気に入りの「{random.choice(self._liked)}」を流す？"
        return self.suggest_by_mood()

    def change_genre(self, genre: str) -> str:
        match = next((g for g in _GENRES if g.lower() in genre.lower()), None)
        if match:
            self._playlist = list(_GENRES[match])
            self._genre    = match
            return self.play(self._playlist[0])
        return f"そのジャンルは見つからなかったよ。Lo-fi, J-Pop, Jazz, Rock, Acoustic, Classicalから選んでね。"

    # ── Status ────────────────────────────────────────────────────────────────
    def status_reply(self) -> str:
        if self._is_playing:
            return f"今「{self._current}」を再生中♪ 音量{self._volume}%。"
        return "今は何も流していないよ。曲をかけようか？"

    # ── Context for prompt ────────────────────────────────────────────────────
    def context_for_prompt(self) -> str:
        status = f"playing '{self._current}'" if self._is_playing else "stopped"
        return (
            f"Music: {status} | Volume: {self._volume}% | "
            f"Genre: {self._genre} | Liked: {len(self._liked)} tracks"
        )
