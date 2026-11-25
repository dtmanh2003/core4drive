import json
import threading
import time
from typing import Optional
import serial
from config import CFG
from state import STATE, log_event

class ArduinoLink:
    def __init__(self):
        self.ser: Optional[serial.Serial] = None
        self.tx_lock = threading.Lock()
        self.reader_started = False
        self.last_error = ""

    def connect(self):
        if self.ser and self.ser.is_open:
            return True
        try:
            self.ser = serial.Serial(CFG.serial_port, CFG.serial_baud, timeout=0.1)
            time.sleep(2.0)  # Arduino reset after USB open
            self.last_error = ""
            if not self.reader_started:
                threading.Thread(target=self._reader_loop, daemon=True).start()
                self.reader_started = True
            print("[serial] connected", CFG.serial_port)
            return True
        except Exception as e:
            self.last_error = str(e)
            print("[serial] connect failed:", e)
            return False

    def _reader_loop(self):
        while True:
            try:
                if not self.ser or not self.ser.is_open:
                    time.sleep(1)
                    self.connect()
                    continue
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        STATE.update_telemetry(data)
                    except Exception as e:
                        print("[serial] bad json", line, e)
                else:
                    print("[arduino]", line)
            except Exception as e:
                print("[serial] reader error:", e)
                time.sleep(1)

    def send(self, cmd: str):
        if not self.connect():
            return False
        try:
            with self.tx_lock:
                self.ser.write((cmd.strip() + "\n").encode("utf-8"))
            return True
        except Exception as e:
            self.last_error = str(e)
            print("[serial] send failed:", e)
            return False

    def unlock(self):
        log_event("ARDUINO_UNLOCK", "sent UNLOCK")
        return self.send("UNLOCK")

    def lock_car(self):
        log_event("ARDUINO_LOCK", "sent LOCK")
        return self.send("LOCK")

    def stop(self):
        return self.send("S")

    def drive(self, left: int, right: int):
        left = max(-CFG.max_motor_cmd, min(CFG.max_motor_cmd, int(left)))
        right = max(-CFG.max_motor_cmd, min(CFG.max_motor_cmd, int(right)))
        # Pi-side safety; Arduino also has its own safety.
        t = STATE.snapshot()["telemetry"]
        dist = t.get("dist")
        if t.get("emg") == 1 or t.get("tilt") == 1 or t.get("impact") == 1:
            self.stop()
            return False
        if (dist is not None and dist > 0 and dist < CFG.obstacle_stop_cm and left > 0 and right > 0) or t.get("ir") == 1:
            self.stop()
            return False
        return self.send(f"D {left} {right}")

    def alarm(self, seconds: int = 5):
        log_event("ALARM", f"sent ALARM {seconds}")
        return self.send(f"ALARM {int(seconds)}")

    def beep(self, ms: int = 140):
        ms = max(20, min(2000, int(ms)))
        log_event("BEEP", f"sent BEEP {ms}ms")
        return self.send(f"BEEP {ms}")

    def mode(self, mode: str):
        return self.send(f"MODE {mode}")

    def servo(self, target: str, angle: int):
        target = str(target).upper()
        if target not in {"CAM", "US", "BOTH"}:
            target = "BOTH"
        angle = max(15, min(165, int(angle)))
        return self.send(f"SERVO {target} {angle}")

    def look(self, where: str):
        where = str(where).upper()
        if where not in {"LEFT", "RIGHT", "CENTER"}:
            where = "CENTER"
        return self.send(f"LOOK {where}")

ARDUINO = ArduinoLink()
