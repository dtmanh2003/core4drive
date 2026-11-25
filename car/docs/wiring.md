# Smart AI Car - Wiring - No OLED / No RGB Version

## Safety first

1. Do **not** power motors from Arduino 5V or Raspberry Pi 5V.
2. Motor battery + goes only to TB6612 VM.
3. Arduino GND, motor battery GND, TB6612 GND must be common.
4. Raspberry Pi connects to Arduino by USB only. Do not connect Arduino 5V output pins to Raspberry Pi GPIO.
6. If using active buzzer, safest is Arduino pin -> 1k resistor -> NPN base, emitter -> GND, collector -> buzzer -, buzzer + -> 5V.
7. Keep motor battery disconnected while uploading code and testing sensors.
8. In this version, do **not** connect OLED or Freenove 8 RGB LED module.

## Architecture

Laptop browser camera -> face registration/verification via web

Raspberry Pi Camera -> car camera live stream + AI lane/parking

Raspberry Pi 4 -> web, camera, face auth, AI, voice, history

Arduino UNO R4 WiFi -> motor, LM393, HC-SR04, IR, emergency button, GY-87, active buzzer

## Arduino pin map

### Encoders

LM393 left D0  -> Arduino D2

LM393 right D0 -> Arduino D3

LM393 VCC -> Arduino 5V

LM393 GND -> GND

### TB6612 #1: left side motors

Left front motor -> AO1/AO2

Left rear motor  -> BO1/BO2

PWMA + PWMB -> Arduino D5

AIN1 + BIN1 -> Arduino D4

AIN2 + BIN2 -> Arduino D7

STBY -> Arduino D10

VCC -> Arduino 5V

VM -> motor battery +

GND -> common GND

### TB6612 #2: right side motors

Right front motor -> AO1/AO2

Right rear motor  -> BO1/BO2

PWMA + PWMB -> Arduino D6

AIN1 + BIN1 -> Arduino D8

AIN2 + BIN2 -> Arduino D9

STBY -> Arduino D10

VCC -> Arduino 5V

VM -> motor battery +

GND -> common GND

### HC-SR04

VCC -> Arduino 5V

GND -> GND

TRIG -> Arduino A0

ECHO -> Arduino A1

### IR obstacle sensor

VCC -> Arduino 5V

GND -> GND

OUT/DO -> Arduino D13

If IR status is reversed, edit firmware:

`bool IR_ACTIVE_LOW = false;`

### Active buzzer

Recommended transistor connection:

Arduino D11 -> 1k resistor -> NPN base

NPN emitter -> GND

NPN collector -> buzzer -

Buzzer + -> 5V

If your active buzzer is tiny and low-current, direct D11 -> buzzer +, buzzer - -> GND may work, but transistor is safer.

### Emergency button

One leg -> Arduino A2

Other leg -> GND

Firmware uses INPUT_PULLUP.

### GY-87

VCC -> follow module label. If unsure and module supports only 3.3V, use 3.3V. Many GY-87 breakout boards support 3V-5V, but check your board print.

GND -> GND

SDA -> Arduino SDA

SCL -> Arduino SCL


## Bản cập nhật servo pan/scan

Bản này thêm 2 servo motor:

```text
- Servo xoay Pi Camera: điều khiển camera nhìn trái/phải từ web.
- Servo xoay HC-SR04: AI dùng để quét trái/phải khi gặp vật cản/ngõ cụt.
```

### Chân mới trên Arduino

```text
Camera servo signal  -> D12
HC-SR04 servo signal -> A4
```

### Cách cấp nguồn servo an toàn

Không nên cấp 2 servo từ Raspberry Pi. Nếu servo nhỏ thì có thể test nhanh bằng 5V Arduino, nhưng khi gắn lên xe nên dùng nguồn 5V riêng hoặc buck converter 5V.

```text
Nguồn 5V servo + -> dây đỏ servo
Nguồn 5V servo - -> dây nâu/đen servo
Arduino GND      -> nối chung với GND servo
Arduino D12      -> signal camera servo
Arduino A4       -> signal HC-SR04 servo
```

### Test servo bằng Serial Monitor

```text
SERVO CAM 90
SERVO CAM 150
SERVO CAM 30
SERVO US 90
SERVO US 150
SERVO US 30
LOOK LEFT
LOOK CENTER
LOOK RIGHT
```

### Web

Web có thêm phần điều khiển servo thủ công:

```text
- Pi Camera servo slider
- HC-SR04 servo slider
- Nhìn trái / Nhìn giữa / Nhìn phải
```

### AI tự di chuyển nâng cấp

Khi gặp vật cản, AI sẽ:

```text
Dừng -> lùi nhẹ -> nhìn trái -> đo khoảng cách -> nhìn phải -> đo khoảng cách -> chọn hướng thoáng hơn -> rẽ -> tiếp tục đi
```
