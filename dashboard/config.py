import os
import json
from PyQt5.QtGui import QColor

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
HABITS_FILE = os.path.join(BASE_DIR, "user_habits.json")
CONFIG_FILE = os.path.join(BASE_DIR, "neuro_config.json")

# ── API key persistence ────────────────────────────────────────────────────────
def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("api_key", "")
    except Exception:
        return ""

def save_api_key(key: str):
    cfg = {}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
    except Exception:
        pass
    cfg["api_key"] = key.strip()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_location() -> dict | None:
    """Return saved home location {lat, lon, city} or None if not set."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "home_lat" in cfg and "home_lon" in cfg:
            return {"lat": cfg["home_lat"], "lon": cfg["home_lon"],
                    "city": cfg.get("home_city", "現在地")}
    except Exception:
        pass
    return None

def save_location(lat: float, lon: float, city: str = "現在地"):
    cfg = {}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
    except Exception:
        pass
    cfg["home_lat"]  = lat
    cfg["home_lon"]  = lon
    cfg["home_city"] = city
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ── Real car connection (smart_ai_car_servo pi_server) ─────────────────────────
def load_car_url() -> str:
    """URL of the pi_server FastAPI (Raspberry Pi car). Default = local test."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("car_server_url", "http://127.0.0.1:8000")
    except Exception:
        return "http://127.0.0.1:8000"

def save_car_url(url: str):
    cfg = {}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
    except Exception:
        pass
    cfg["car_server_url"] = url.strip()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ── Qt Styles ─────────────────────────────────────────────────────────────────
STYLE_MAIN = """
QMainWindow, QWidget {
    background-color: #0a0e1a;
    color: #e0e8ff;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QScrollBar:vertical {
    background: #0d1120;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2a4a8a;
    border-radius: 3px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

PANEL_STYLE = """
QFrame {
    background-color: #0d1120;
    border: 1px solid #1a2a4a;
    border-radius: 12px;
}
"""

# ── Neon color palette ─────────────────────────────────────────────────────────
NEON_BLUE   = QColor(0, 170, 255)
NEON_PURPLE = QColor(130, 0, 255)
NEON_GREEN  = QColor(0, 255, 140)
NEON_ORANGE = QColor(255, 140, 0)
NEON_RED    = QColor(255, 40, 40)
DIM_BLUE    = QColor(15, 25, 55)
