import threading
import time
from typing import Optional
import cv2

class Camera:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.running = False
        self.thread = None
        self.picam2 = None
        self.cv_cap = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _init_camera(self):
        try:
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            cfg = self.picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
            self.picam2.configure(cfg)
            self.picam2.start()
            time.sleep(1)
            print("[camera] using Picamera2")
            return
        except Exception as e:
            print("[camera] Picamera2 not available, fallback to cv2:", e)
        self.cv_cap = cv2.VideoCapture(0)
        self.cv_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cv_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("[camera] using cv2.VideoCapture(0)")

    def _loop(self):
        self._init_camera()
        while self.running:
            frame = None
            try:
                if self.picam2 is not None:
                    rgb = self.picam2.capture_array()
                    frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                elif self.cv_cap is not None:
                    ok, frame = self.cv_cap.read()
                    if not ok:
                        frame = None
            except Exception as e:
                print("[camera] read error:", e)
                frame = None
            if frame is not None:
                with self.lock:
                    self.frame = frame
            time.sleep(0.03)

    def get_frame(self) -> Optional[object]:
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def mjpeg_generator(self):
        self.start()
        while True:
            frame = self.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if not ok:
                continue
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            time.sleep(0.04)

CAMERA = Camera()
