import sqlite3
import time
from pathlib import Path
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FAILED_DIR = DATA_DIR / "failed_faces"
DB_PATH = DATA_DIR / "events.db"
DATA_DIR.mkdir(exist_ok=True)
FAILED_DIR.mkdir(exist_ok=True)

class CarState:
    def __init__(self):
        self.lock = Lock()
        self.unlocked = False
        self.mode = "LOCKED"  # LOCKED, WEB, VOICE, AI_LANE, AUTO_PARK, ALARM, EMERGENCY
        self.face_failures = 0
        self.telemetry = {
            "speedL": 0.0,
            "speedR": 0.0,
            "speed": 0.0,
            "rpmL": 0.0,
            "rpmR": 0.0,
            "dist": None,
            "ir": 0,
            "emg": 0,
            "tilt": 0,
            "impact": 0,
            "arduinoLocked": 1,
            "ts": 0,
        }
        self.ai_task_running = False

    def snapshot(self):
        with self.lock:
            return {
                "unlocked": self.unlocked,
                "mode": self.mode,
                "face_failures": self.face_failures,
                "telemetry": dict(self.telemetry),
            }

    def set_mode(self, mode: str):
        with self.lock:
            self.mode = mode

    def set_unlocked(self, value: bool):
        with self.lock:
            self.unlocked = value
            self.mode = "WEB" if value else "LOCKED"
            if value:
                self.face_failures = 0

    def add_face_failure(self):
        with self.lock:
            self.face_failures += 1
            return self.face_failures

    def reset_failures(self):
        with self.lock:
            self.face_failures = 0

    def update_telemetry(self, data: dict):
        with self.lock:
            self.telemetry.update(data)
            self.telemetry["ts"] = time.time()
            if data.get("emg") == 1:
                self.mode = "EMERGENCY"

STATE = CarState()

def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            event TEXT NOT NULL,
            detail TEXT,
            image_path TEXT
        )
    """)
    con.commit()
    con.close()


def log_event(event: str, detail: str = "", image_path: str | None = None):
    init_db()
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO events(ts,event,detail,image_path) VALUES(?,?,?,?)",
        (time.time(), event, detail, image_path),
    )
    con.commit()
    con.close()


def list_events(limit: int = 100):
    init_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]

init_db()
