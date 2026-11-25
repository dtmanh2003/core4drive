import base64
import json
import sqlite3
import time
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np
from config import CFG
from state import DATA_DIR, FAILED_DIR, log_event

FACE_DB = DATA_DIR / "faces.db"

class FaceAuth:
    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)
        self._init_db()
        self.users = self._load_users()

    def _init_db(self):
        DATA_DIR.mkdir(exist_ok=True)
        con = sqlite3.connect(FACE_DB)
        con.execute("""
            CREATE TABLE IF NOT EXISTS face_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                templates_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        con.commit(); con.close()

    def _load_users(self):
        self._init_db()
        con = sqlite3.connect(FACE_DB)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM face_users ORDER BY id ASC").fetchall()
        con.close()
        users = []
        for r in rows:
            try:
                arrs = json.loads(r["templates_json"])
                templates = [np.array(x, dtype=np.float32) for x in arrs]
                users.append({"id": r["id"], "name": r["name"], "templates": templates})
            except Exception:
                continue
        return users

    def list_users(self):
        self.users = self._load_users()
        return [{"id": u["id"], "name": u["name"], "template_count": len(u["templates"])} for u in self.users]

    def delete_user(self, user_id: int):
        self._init_db()
        con = sqlite3.connect(FACE_DB)
        cur = con.execute("DELETE FROM face_users WHERE id=?", (int(user_id),))
        con.commit(); con.close()
        self.users = self._load_users()
        log_event("FACE_USER_DELETE", f"user_id={user_id}")
        return {"ok": cur.rowcount > 0}

    def _save_user(self, name: str, templates: List[np.ndarray]):
        now = time.time()
        templates_json = json.dumps([t.tolist() for t in templates])
        con = sqlite3.connect(FACE_DB)
        cur = con.execute(
            "INSERT INTO face_users(name,templates_json,created_at,updated_at) VALUES(?,?,?,?)",
            (name, templates_json, now, now),
        )
        con.commit(); user_id = cur.lastrowid; con.close()
        self.users = self._load_users()
        return user_id

    def _decode_data_url(self, data_url: str):
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        raw = base64.b64decode(data_url)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img

    def _extract_face_embedding(self, img) -> Tuple[bool, np.ndarray | None, object | None]:
        if img is None:
            return False, None, None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return False, None, None
        x, y, w, h = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)[0]
        pad = int(0.12 * w)
        x1 = max(0, x - pad); y1 = max(0, y - pad)
        x2 = min(gray.shape[1], x + w + pad); y2 = min(gray.shape[0], y + h + pad)
        crop = gray[y1:y2, x1:x2]
        crop = cv2.resize(crop, (96, 96))
        crop = cv2.equalizeHist(crop)
        vec = crop.astype(np.float32).flatten() / 255.0
        vec = vec - vec.mean()
        norm = np.linalg.norm(vec) + 1e-6
        vec = vec / norm
        return True, vec, (x1, y1, x2, y2)

    def register(self, name: str, data_urls: List[str]):
        name = (name or "").strip()
        if not name:
            return {"ok": False, "message": "Bạn phải nhập tên trước khi đăng ký mặt"}
        templates = []
        total = 0
        for d in data_urls:
            total += 1
            img = self._decode_data_url(d)
            ok, emb, _ = self._extract_face_embedding(img)
            if ok and emb is not None:
                templates.append(emb)
        if len(templates) < max(5, CFG.face_samples_needed // 3):
            log_event("FACE_REGISTER_FAIL", f"name={name} usable={len(templates)} total={total}")
            return {"ok": False, "message": f"Không đủ mẫu mặt rõ: {len(templates)}/{total}"}
        user_id = self._save_user(name, templates)
        log_event("FACE_REGISTER_OK", f"user_id={user_id} name={name} samples={len(templates)}")
        return {"ok": True, "user_id": user_id, "name": name, "message": f"Đã đăng ký {name} với {len(templates)} mẫu khuôn mặt"}

    def verify(self, data_url: str):
        self.users = self._load_users()
        img = self._decode_data_url(data_url)
        if not self.users:
            log_event("FACE_VERIFY_FAIL", "no registered user")
            return {"ok": False, "reason": "NO_REGISTERED_FACE", "distance": None}
        ok, emb, box = self._extract_face_embedding(img)
        if not ok or emb is None:
            path = self.save_failed_image(img, "no_face")
            log_event("FACE_VERIFY_FAIL", "no face detected", str(path))
            return {"ok": False, "reason": "NO_FACE", "distance": None, "image_path": str(path)}

        best = {"distance": 999.0, "user_id": None, "name": None}
        for u in self.users:
            for t in u["templates"]:
                dist = float(np.linalg.norm(emb - t))
                if dist < best["distance"]:
                    best = {"distance": dist, "user_id": u["id"], "name": u["name"]}

        dist = best["distance"]
        passed = dist <= CFG.face_distance_threshold
        if passed:
            log_event("FACE_VERIFY_OK", f"user_id={best['user_id']} name={best['name']} distance={dist:.4f}")
            return {"ok": True, "reason": "OK", "distance": dist, "user_id": best["user_id"], "name": best["name"]}
        path = self.save_failed_image(img, f"dist_{dist:.3f}")
        log_event("FACE_VERIFY_FAIL", f"nearest={best['name']} distance={dist:.4f}", str(path))
        return {"ok": False, "reason": "NOT_MATCH", "distance": dist, "nearest_name": best["name"], "image_path": str(path)}

    def save_failed_image(self, img, reason: str):
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        name = time.strftime("failed_%Y%m%d_%H%M%S_") + reason.replace("/", "_") + ".jpg"
        path = FAILED_DIR / name
        if img is not None:
            cv2.imwrite(str(path), img)
        return path

FACE = FaceAuth()
