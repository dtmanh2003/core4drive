from dataclasses import dataclass

@dataclass
class Config:
    serial_port: str = "/dev/ttyACM0"
    serial_baud: int = 115200

    # Face auth: laptop webcam image is sent from browser to this server.
    face_samples_needed: int = 18
    face_distance_threshold: float = 0.42
    face_lockout_failures: int = 3

    # Buzzer: wrong face = one short beep. Active buzzers do not have true volume control,
    # so we control duration here. Make it smaller if it is too loud/annoying.
    wrong_face_beep_ms: int = 140

    # Manual control default speed command. Web slider can override this.
    default_manual_speed: int = 120

    # AI lane: default = green tape/path. Tune on web later if needed.
    lane_hsv_lower: tuple = (35, 45, 35)
    lane_hsv_upper: tuple = (90, 255, 255)
    lane_base_speed: int = 90
    lane_turn_gain: float = 85.0

    # Auto roam / wander mode
    roam_speed: int = 75
    roam_turn_speed: int = 75
    roam_reverse_ms: int = 350
    roam_turn_ms: int = 520

    # Servos for Pi Camera pan and HC-SR04 pan
    servo_min_angle: int = 15
    servo_max_angle: int = 165
    servo_center_angle: int = 90
    servo_settle_ms: int = 350

    # Auto park marker
    aruco_marker_id: int = 7
    park_stop_marker_area: int = 14500
    park_stop_distance_cm: float = 18.0

    # Safety limits
    obstacle_stop_cm: float = 15.0
    obstacle_slow_cm: float = 28.0
    max_motor_cmd: int = 180

    # PiPower 5 I2C battery monitor. Official docs list 0x5C and battery percentage register.
    pipower_i2c_bus: int = 1
    pipower_i2c_addr: int = 0x5C
    pipower_enabled: bool = True

CFG = Config()
