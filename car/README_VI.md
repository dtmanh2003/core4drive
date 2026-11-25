# Smart AI Car Plus - no OLED/RGB/audio

Bản này dùng:

- Raspberry Pi 4 + Pi Camera: web, camera live, AI, tự đỗ, lịch sử, đọc PiPower5.
- Laptop webcam: đăng ký/xác nhận khuôn mặt.
- Arduino UNO R4 WiFi: motor, LM393, HC-SR04, IR obstacle, active buzzer, emergency button, GY-87, đọc pin motor.

Không dùng: OLED, Freenove 8 RGB LED, speaker, amplifier, keypad, joystick, PIR, photoresistor, tilt/vibration switch, ESP32.

## Tính năng thêm trong bản Plus

- Hiển thị tốc độ m/s và m/min.
- Hiển thị PiPower5 nếu I2C đọc được.
- Hiển thị pin motor qua chân A3 Arduino bằng mạch chia áp.
- Sai mặt chỉ kêu 1 tiếng bíp ngắn.
- Có thanh chỉnh tốc độ trên web.
- Đăng ký khuôn mặt kèm tên, lưu vĩnh viễn vào database `pi_server/data/faces.db`.
- Có danh sách faces đã lưu và nút xóa.
- Voice control tiếng Việt và tiếng Nhật.
- Thêm chế độ AI tự di chuyển xung quanh / roam.

## An toàn nguồn điện

- Không cấp motor từ Raspberry Pi.
- Không cấp motor từ Arduino 5V.
- Pin motor + chỉ nối vào VM của TB6612FNG.
- GND Arduino + GND pin motor + GND TB6612 phải nối chung.
- Raspberry Pi nối Arduino bằng USB thôi.
- Không nối digital 5V Arduino vào GPIO Raspberry Pi.
- Active buzzer nên đi qua transistor nếu loại to.
- Đọc pin motor trên A3 bắt buộc dùng mạch chia áp, không nối pin motor trực tiếp vào A3.

## Nối pin motor vào A3 để đo pin

Dùng chia áp:

```text
Motor battery + ---- R1 100kΩ ----+---- Arduino A3
                                  |
                                R2 47kΩ
                                  |
GND ------------------------------+
```

GND motor battery vẫn phải nối chung với Arduino GND.

Trong firmware Arduino, mặc định đang đặt cho pin motor 4xAA:

```cpp
const float MOTOR_BAT_EMPTY_V = 4.8;
const float MOTOR_BAT_FULL_V  = 6.4;
```

Nếu dùng 2xAA thì đổi thành khoảng 2.0 và 3.2. Nếu dùng 2x18650 thì đổi thành 6.4 và 8.4.

## PiPower5

Bản này đọc PiPower5 qua I2C địa chỉ 0x5C. Cần bật I2C:

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
sudo reboot
```

Kiểm tra:

```bash
sudo i2cdetect -y 1
```

Nếu thấy `5c` thì web có thể hiện pin PiPower5. Nếu không, web sẽ hiện N/A.

## Cài trên Raspberry Pi

```bash
cd ~
unzip smart_ai_car_plus.zip
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-picamera2 unzip i2c-tools
cd ~/smart_ai_car_plus/pi_server
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Upload Arduino

Mở:

```text
arduino_firmware/smart_car_r4_no_display/smart_car_r4_no_display.ino
```

Board: Arduino UNO R4 WiFi.

Bản này không cần thư viện Arduino ngoài.

## Chạy server

```bash
cd ~/smart_ai_car_plus/pi_server
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Mở bằng laptop. Để bật được webcam laptop, nên dùng SSH tunnel:

```powershell
ssh -L 8000:127.0.0.1:8000 raspi4jcool@IP_RASPBERRY_PI
```

Rồi mở:

```text
http://localhost:8000
```

## Test thứ tự

1. Upload Arduino.
2. Mở Serial Monitor, gửi `UNLOCK`, `D 80 80`, `S`, `BEEP 100`.
3. Test Pi Camera bằng `libcamera-hello`.
4. Chạy server.
5. Mở web bằng laptop qua `localhost` tunnel.
6. Bật camera laptop.
7. Nhập tên và đăng ký mặt.
8. Xác nhận mặt.
9. Test thanh tốc độ + nút điều khiển.
10. Test sai mặt: chỉ bíp 1 cái, ảnh sai được lưu.
11. Test m/min, pin motor, PiPower5.
12. Test voice Việt/Nhật.
13. Test AI bám đường, AI tự di chuyển, AI tự đỗ.

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
