import asyncio
import cv2
import numpy as np
from config import CFG
from camera import CAMERA
from serial_link import ARDUINO
from state import STATE, log_event


def _safe_to_move_forward():
    t = STATE.snapshot()["telemetry"]
    dist = t.get("dist")
    if t.get("emg") == 1 or t.get("tilt") == 1 or t.get("impact") == 1:
        return False
    if t.get("ir") == 1:
        return False
    if dist is not None and dist > 0 and dist < CFG.obstacle_stop_cm:
        return False
    return True


def _get_distance():
    d = STATE.snapshot()["telemetry"].get("dist")
    try:
        return float(d)
    except Exception:
        return -1.0


async def _look_center():
    ARDUINO.look("CENTER")
    await asyncio.sleep(0.25)


async def _scan_left_right():
    """Turn both camera and HC-SR04 left/right, then return best direction.

    Return: "LEFT", "RIGHT", or "CENTER". Higher distance is considered better.
    """
    ARDUINO.look("LEFT")
    await asyncio.sleep(CFG.servo_settle_ms / 1000.0)
    left_dist = _get_distance()

    ARDUINO.look("RIGHT")
    await asyncio.sleep(CFG.servo_settle_ms / 1000.0)
    right_dist = _get_distance()

    await _look_center()
    log_event("AI_SCAN", f"left={left_dist:.1f} right={right_dist:.1f}")

    # Treat invalid distance as blocked/unknown.
    l = left_dist if left_dist > 0 else -1
    r = right_dist if right_dist > 0 else -1
    if l < 0 and r < 0:
        return "CENTER"
    if l >= r:
        return "LEFT"
    return "RIGHT"


async def lane_follow_loop():
    log_event("AI_LANE_START", "")
    ARDUINO.mode("AI_LANE")
    ARDUINO.look("CENTER")
    while STATE.snapshot()["mode"] == "AI_LANE" and STATE.snapshot()["unlocked"]:
        if not _safe_to_move_forward():
            ARDUINO.stop()
            # Look around briefly; then rotate toward the clearer side.
            best = await _scan_left_right()
            if best == "LEFT":
                ARDUINO.drive(-CFG.roam_turn_speed, CFG.roam_turn_speed)
            elif best == "RIGHT":
                ARDUINO.drive(CFG.roam_turn_speed, -CFG.roam_turn_speed)
            await asyncio.sleep(0.35)
            ARDUINO.stop()
            await asyncio.sleep(0.15)
            continue
        frame = CAMERA.get_frame()
        if frame is None:
            ARDUINO.stop(); await asyncio.sleep(0.1); continue
        h, w = frame.shape[:2]
        roi = frame[int(h*0.55):h, :]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(CFG.lane_hsv_lower), np.array(CFG.lane_hsv_upper))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
        m = cv2.moments(mask)
        if m["m00"] < 500:
            # Lost line: sweep camera a little and rotate slowly to search.
            ARDUINO.servo("CAM", 60)
            await asyncio.sleep(0.10)
            ARDUINO.servo("CAM", 120)
            await asyncio.sleep(0.10)
            ARDUINO.servo("CAM", 90)
            ARDUINO.drive(-55, 55)
        else:
            cx = int(m["m10"] / m["m00"])
            error = (cx - w/2) / (w/2)
            turn = int(error * CFG.lane_turn_gain)
            base = CFG.lane_base_speed
            ARDUINO.drive(base + turn, base - turn)
        await asyncio.sleep(0.08)
    ARDUINO.stop()
    ARDUINO.look("CENTER")
    log_event("AI_LANE_STOP", "")


def _detect_aruco(frame):
    try:
        aruco = cv2.aruco
        dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        params = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(dictionary, params)
        corners, ids, _ = detector.detectMarkers(frame)
        if ids is None:
            return None
        for c, i in zip(corners, ids.flatten()):
            if int(i) == CFG.aruco_marker_id:
                pts = c[0]
                cx = int(pts[:,0].mean())
                area = float(cv2.contourArea(pts.astype(np.float32)))
                return cx, area
    except Exception:
        pass
    return None


async def auto_park_loop():
    log_event("AUTO_PARK_START", "")
    ARDUINO.mode("AUTO_PARK")
    ARDUINO.look("CENTER")
    search_angles = [90, 60, 120, 45, 135]
    search_i = 0
    while STATE.snapshot()["mode"] == "AUTO_PARK" and STATE.snapshot()["unlocked"]:
        t = STATE.snapshot()["telemetry"]
        dist = t.get("dist")
        if t.get("emg") == 1 or t.get("tilt") == 1 or t.get("impact") == 1 or t.get("ir") == 1:
            ARDUINO.stop(); await asyncio.sleep(0.15); continue
        frame = CAMERA.get_frame()
        if frame is None:
            ARDUINO.stop(); await asyncio.sleep(0.1); continue
        h, w = frame.shape[:2]
        det = _detect_aruco(frame)
        if det is None:
            # Sweep camera to find marker, while rotating very slowly.
            angle = search_angles[search_i % len(search_angles)]
            search_i += 1
            ARDUINO.servo("CAM", angle)
            ARDUINO.drive(40, -40)
            await asyncio.sleep(0.22)
        else:
            # Center camera before approaching.
            ARDUINO.servo("CAM", 90)
            cx, area = det
            if area > CFG.park_stop_marker_area or (dist is not None and dist > 0 and dist < CFG.park_stop_distance_cm):
                ARDUINO.stop()
                STATE.set_mode("PARKED")
                ARDUINO.mode("PARKED")
                ARDUINO.look("CENTER")
                log_event("AUTO_PARK_DONE", f"area={area} dist={dist}")
                break
            error = (cx - w/2) / (w/2)
            turn = int(error * 65)
            base = 55
            ARDUINO.drive(base + turn, base - turn)
        await asyncio.sleep(0.10)
    ARDUINO.stop()
    ARDUINO.look("CENTER")
    log_event("AUTO_PARK_STOP", "")


async def roam_loop():
    """Autonomous roaming with active sensor/camera scanning.

    The HC-SR04 servo looks left/right when blocked, chooses the more open side,
    then the car turns toward that side. The camera servo follows the same scan
    so you can see what the car is checking on the web.
    """
    import random
    log_event("AI_ROAM_START", "")
    ARDUINO.mode("AI_ROAM")
    ARDUINO.look("CENTER")
    while STATE.snapshot()["mode"] == "AI_ROAM" and STATE.snapshot()["unlocked"]:
        t = STATE.snapshot()["telemetry"]
        dist = t.get("dist")
        blocked = (
            t.get("emg") == 1 or t.get("tilt") == 1 or t.get("impact") == 1 or
            t.get("ir") == 1 or
            (dist is not None and dist > 0 and dist < CFG.obstacle_slow_cm)
        )
        if blocked:
            ARDUINO.stop()
            await asyncio.sleep(0.10)
            # Back up a little before scanning, so the servo has space to look.
            ARDUINO.drive(-CFG.roam_speed, -CFG.roam_speed)
            await asyncio.sleep(CFG.roam_reverse_ms / 1000.0)
            ARDUINO.stop()
            await asyncio.sleep(0.08)

            best = await _scan_left_right()
            if best == "LEFT":
                ARDUINO.drive(-CFG.roam_turn_speed, CFG.roam_turn_speed)
            elif best == "RIGHT":
                ARDUINO.drive(CFG.roam_turn_speed, -CFG.roam_turn_speed)
            else:
                # Unknown: choose random direction.
                if random.random() < 0.5:
                    ARDUINO.drive(-CFG.roam_turn_speed, CFG.roam_turn_speed)
                else:
                    ARDUINO.drive(CFG.roam_turn_speed, -CFG.roam_turn_speed)
            await asyncio.sleep(CFG.roam_turn_ms / 1000.0)
            ARDUINO.stop()
            await asyncio.sleep(0.08)
        else:
            ARDUINO.look("CENTER")
            steer = random.choice([-10, -5, 0, 5, 10])
            ARDUINO.drive(CFG.roam_speed + steer, CFG.roam_speed - steer)
            await asyncio.sleep(0.35)
    ARDUINO.stop()
    ARDUINO.look("CENTER")
    log_event("AI_ROAM_STOP", "")
