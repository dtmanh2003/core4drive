import asyncio
from pathlib import Path
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from camera import CAMERA
from face_auth import FACE
from serial_link import ARDUINO
from state import STATE, log_event, list_events, FAILED_DIR
from config import CFG
from ai_drive import lane_follow_loop, auto_park_loop, roam_loop
from battery import PIPOWER5

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Smart AI Car Plus")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class FaceRegisterRequest(BaseModel):
    name: str
    images: List[str]

class FaceVerifyRequest(BaseModel):
    image: str

class DriveRequest(BaseModel):
    left: int
    right: int

class BeepRequest(BaseModel):
    ms: int = 140

class ServoRequest(BaseModel):
    target: str = "BOTH"  # CAM / US / BOTH
    angle: int = 90

@app.on_event("startup")
async def startup():
    CAMERA.start()
    ARDUINO.connect()
    ARDUINO.lock_car()
    STATE.set_unlocked(False)
    log_event("SYSTEM_START", "server started")

@app.get("/")
async def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(CAMERA.mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/status")
async def status():
    s = STATE.snapshot()
    s["serial_error"] = ARDUINO.last_error
    s["pipower5"] = PIPOWER5.read()
    return s

@app.get("/api/events")
async def events(limit: int = 100):
    return {"events": list_events(limit)}

@app.get("/api/faces")
async def faces():
    return {"users": FACE.list_users()}

@app.delete("/api/faces/{user_id}")
async def delete_face(user_id: int):
    return FACE.delete_user(user_id)

@app.get("/api/failed_face/{filename}")
async def failed_face(filename: str):
    path = FAILED_DIR / filename
    if path.exists():
        return FileResponse(path)
    return JSONResponse({"ok": False, "error": "not found"}, status_code=404)

@app.post("/api/face/register")
async def face_register(req: FaceRegisterRequest):
    result = FACE.register(req.name, req.images)
    return result

@app.post("/api/face/verify")
async def face_verify(req: FaceVerifyRequest):
    result = FACE.verify(req.image)
    if result.get("ok"):
        STATE.set_unlocked(True)
        ARDUINO.unlock()
        ARDUINO.mode("WEB")
        log_event("UNLOCK", f"face user={result.get('name')}")
        return {**result, "unlocked": True}

    failures = STATE.add_face_failure()
    # New behavior: wrong face = one short beep only.
    ARDUINO.beep(CFG.wrong_face_beep_ms)
    if failures >= CFG.face_lockout_failures:
        STATE.set_unlocked(False)
        STATE.set_mode("ALARM")
        ARDUINO.lock_car()
        log_event("FACE_ALARM", f"failures={failures}", result.get("image_path"))
    return {**result, "unlocked": False, "failures": failures}

@app.post("/api/lock")
async def lock():
    STATE.set_unlocked(False)
    ARDUINO.lock_car()
    ARDUINO.stop()
    log_event("LOCK", "manual lock")
    return {"ok": True}

@app.post("/api/stop")
async def stop():
    ARDUINO.stop()
    if STATE.snapshot()["unlocked"]:
        STATE.set_mode("WEB")
        ARDUINO.mode("WEB")
    log_event("STOP", "web stop")
    return {"ok": True}

@app.post("/api/drive")
async def drive(req: DriveRequest):
    if not STATE.snapshot()["unlocked"]:
        ARDUINO.stop()
        return JSONResponse({"ok": False, "error": "LOCKED"}, status_code=403)
    STATE.set_mode("WEB")
    ARDUINO.mode("WEB")
    ok = ARDUINO.drive(req.left, req.right)
    return {"ok": ok}

@app.post("/api/beep")
async def beep(req: BeepRequest):
    ARDUINO.beep(req.ms)
    return {"ok": True}

@app.post("/api/servo")
async def servo(req: ServoRequest):
    ok = ARDUINO.servo(req.target, req.angle)
    return {"ok": ok, "target": req.target.upper(), "angle": max(15, min(165, int(req.angle)))}

@app.post("/api/look/{where}")
async def look(where: str):
    ok = ARDUINO.look(where)
    return {"ok": ok, "where": where.upper()}

@app.post("/api/alarm_test")
async def alarm_test():
    # Kept for compatibility, but now it is just one short beep.
    ARDUINO.beep(CFG.wrong_face_beep_ms)
    return {"ok": True}

@app.post("/api/voice_mode")
async def voice_mode():
    if not STATE.snapshot()["unlocked"]:
        return JSONResponse({"ok": False, "error": "LOCKED"}, status_code=403)
    STATE.set_mode("VOICE")
    ARDUINO.mode("VOICE")
    return {"ok": True}

@app.post("/api/ai/lane")
async def ai_lane():
    if not STATE.snapshot()["unlocked"]:
        return JSONResponse({"ok": False, "error": "LOCKED"}, status_code=403)
    STATE.set_mode("AI_LANE")
    asyncio.create_task(lane_follow_loop())
    return {"ok": True}

@app.post("/api/ai/park")
async def ai_park():
    if not STATE.snapshot()["unlocked"]:
        return JSONResponse({"ok": False, "error": "LOCKED"}, status_code=403)
    STATE.set_mode("AUTO_PARK")
    asyncio.create_task(auto_park_loop())
    return {"ok": True}

@app.post("/api/ai/roam")
async def ai_roam():
    if not STATE.snapshot()["unlocked"]:
        return JSONResponse({"ok": False, "error": "LOCKED"}, status_code=403)
    STATE.set_mode("AI_ROAM")
    asyncio.create_task(roam_loop())
    return {"ok": True}

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            s = STATE.snapshot()
            s["pipower5"] = PIPOWER5.read()
            await ws.send_json(s)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
