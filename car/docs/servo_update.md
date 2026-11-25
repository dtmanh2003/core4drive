# Servo update: Pi Camera pan + HC-SR04 pan

Bản này thêm 2 servo motor:

- Servo 1: xoay Pi Camera trái/phải.
- Servo 2: xoay HC-SR04 trái/phải.

## Cảnh báo nguồn servo

Không cấp 2 servo trực tiếp từ Raspberry Pi. Không lấy nguồn servo từ chân 5V Arduino nếu servo giật mạnh hoặc reset board.

Khuyến nghị dùng nguồn 5V riêng hoặc buck converter 5V từ pin motor:

```text
Nguồn 5V servo +  -> dây đỏ của 2 servo
Nguồn 5V servo -  -> GND servo
Arduino GND       -> nối chung GND servo
Arduino signal    -> dây tín hiệu servo
```

Nếu test tạm 1 servo nhỏ SG90, có thể thử từ 5V Arduino, nhưng khi gắn 2 servo lên xe nên dùng nguồn 5V riêng 1A-2A.

## Nối dây servo

Servo thường có 3 dây:

```text
Nâu/Đen   = GND
Đỏ        = 5V
Cam/Vàng  = Signal
```

Kết nối:

```text
Camera servo signal  -> Arduino D12
HC-SR04 servo signal -> Arduino A4
Servo đỏ             -> 5V servo riêng
Servo nâu/đen        -> GND servo riêng
GND servo riêng      -> GND Arduino
```

## Lệnh Serial mới

```text
SERVO CAM 90     -> xoay camera về giữa
SERVO US 90      -> xoay HC-SR04 về giữa
SERVO BOTH 90    -> xoay cả 2 servo về giữa
LOOK LEFT        -> cả camera và HC-SR04 nhìn trái
LOOK CENTER      -> nhìn giữa
LOOK RIGHT       -> nhìn phải
```

Góc được giới hạn từ 15 đến 165 độ để tránh kẹt cơ khí.

## Web

Web có thêm phần `Camera / HC-SR04 Servo`:

- Thanh trượt Pi Camera servo.
- Thanh trượt HC-SR04 servo.
- Nút Nhìn trái / Nhìn giữa / Nhìn phải.
- Dashboard hiển thị góc servo hiện tại.

## AI tự di chuyển

Trong chế độ AI tự di chuyển:

1. Xe gặp vật cản hoặc ngõ cụt.
2. Xe lùi nhẹ.
3. Camera + HC-SR04 quay trái để đo khoảng cách.
4. Camera + HC-SR04 quay phải để đo khoảng cách.
5. Xe chọn phía thông thoáng hơn để rẽ.
6. Servo quay lại giữa rồi xe tiếp tục đi.
