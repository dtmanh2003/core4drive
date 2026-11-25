# Kịch bản video giới thiệu đồ án — Smart AI Car Plus (bản 3 phút)

**Thời lượng mục tiêu:** 3:00
**Định dạng:** quay ngang 16:9, 1080p
**Chuẩn bị trước khi quay:**

- Sạc đầy pin motor. Server Pi đang chạy, web mở sẵn trên laptop (SSH tunnel `localhost:8000`).
- Đăng ký sẵn 1 khuôn mặt để verify nhanh, nhưng vẫn quay cảnh đăng ký.
- In marker ArUco (ID 7), dán băng keo xanh lá làm đường, đặt sẵn 2 hộp giấy làm vật cản.
- Ánh sáng đều (nhận mặt nhạy sáng — quay ban ngày hoặc đèn trần sáng).
- **Quay demo AI trước, nhiều lần, chọn take đẹp nhất** — lúc dựng chỉ ghép, không chờ xe "diễn" đúng.
- Đồ họa chèn: 5 hình trong artifact "Smart AI Car Plus — Đồ họa video".

**Ký hiệu:** 🎥 = cảnh quay, 🎙 = lời thoại (đọc vừa phải, rõ), 🖼 = chèn đồ họa.

---

## Cảnh 1 — Mở đầu (0:00 – 0:15)

🎥 Cận cảnh xe trên sàn, lia máy quanh xe 2–3 giây, cắt sang đoạn xe tự chạy né vật cản đẹp nhất (lấy từ footage roam quay trước).

🖼 **Hình 1 — Title card** đè lên 3 giây đầu.

🎙
> "Đây là Smart AI Car Plus — xe tự hành mini điều khiển qua web: mở khóa bằng khuôn mặt, nghe lệnh giọng nói, và tự lái với ba chế độ AI. Toàn bộ từ firmware đến giao diện web do em tự thiết kế và lập trình."

---

## Cảnh 2 — Kiến trúc hệ thống (0:15 – 0:45)

🖼 **Hình 2 — Sơ đồ kiến trúc** toàn màn hình, dùng con trỏ chỉ từng khối khi nói. Xen 2 giây cận cảnh Pi + Arduino thật trên xe.

🎙
> "Hệ thống có ba tầng. Laptop chạy giao diện web và dùng webcam để xác thực khuôn mặt. Raspberry Pi là bộ não: server FastAPI, xử lý ảnh OpenCV từ Pi Camera, chạy thuật toán AI. Arduino lo phần thời gian thực: động cơ, hai servo, và các cảm biến an toàn. Pi và Arduino trao đổi qua USB — Arduino gửi dữ liệu cảm biến bốn lần mỗi giây."

---

## Cảnh 3 — Mở khóa bằng khuôn mặt (0:45 – 1:15)

🎥 Screen record màn hình laptop, tua nhanh phần chờ:
1. Nhập tên → bấm **Đăng ký mặt** (tua nhanh 18 mẫu còn ~3 giây).
2. Bấm **Xác nhận mặt** → badge chuyển UNLOCKED.
3. Người khác thử → cận cảnh xe **bíp** + dòng log FACE_VERIFY_FAIL kèm ảnh chụp lại.

🎙
> "Xe mặc định bị khóa — mọi lệnh chạy đều bị chặn ở cả Pi lẫn Arduino. Đăng ký khuôn mặt qua webcam, hệ thống lưu mười tám mẫu vào database. Đúng mặt thì mở khóa; sai mặt thì xe bíp cảnh báo và tự chụp ảnh người lạ vào nhật ký — sai ba lần là khóa cứng."

---

## Cảnh 4 — Điều khiển: tay + giọng nói (1:15 – 1:45)

🎥 Nửa đầu: bấm nút tiến/lùi, kéo thanh tốc độ, kéo slider servo — cận cảnh camera trên xe xoay theo, lướt qua dashboard (tốc độ, khoảng cách, pin). Nửa sau: nói "Tiến" → xe tiến, "Dừng" → xe dừng, thêm một lệnh tiếng Nhật "止まれ".

🎙
> "Giao diện web điều khiển xe thời gian thực: chỉnh tốc độ, xoay camera, và bảng đồng hồ hiển thị tốc độ đo bằng encoder, khoảng cách vật cản, mức pin. Xe còn nghe được giọng nói — cả tiếng Việt lẫn tiếng Nhật: tiến, lùi, dừng, quay camera, kích hoạt chế độ AI."

---

## Cảnh 5 — Ba chế độ AI (1:45 – 2:30)

🖼 **Hình 3 — Thẻ 3 chế độ AI** chèn 2 giây trước khi vào demo. Mỗi chế độ ~14 giây, chỉ lấy khoảnh khắc đắt nhất:

1. **Bám đường:** góc trên cao, xe ôm theo vạch xanh qua khúc cua.
2. **Tự do khám phá:** xe gặp hộp → lùi → **servo quét trái–phải** (cận cảnh, cảnh đắt giá nhất) → rẽ hướng thoáng.
3. **Tự đỗ:** xe quay tìm marker ArUco, thấy là tiến thẳng vào và dừng đúng cự ly.

🎙
> "Ba chế độ AI. Một — bám đường: camera lọc màu tách vạch kẻ và tự điều chỉnh hai bánh ôm theo đường. Hai — tự do khám phá: gặp vật cản, xe xoay cảm biến siêu âm quét hai bên, đo khoảng cách rồi rẽ về hướng thoáng hơn. Ba — tự đỗ: xe quét tìm marker ArUco, căn giữa, tiến vào và dừng đúng khoảng cách an toàn."

---

## Cảnh 6 — An toàn (2:30 – 2:50)

🖼 **Hình 4 — Năm lớp bảo vệ** chèn 2 giây, rồi hai demo chớp nhoáng:
1. Đưa hộp chắn trước xe đang tiến → xe tự dừng.
2. Bấm nút khẩn cấp → xe dừng ngay, web hiện EMERGENCY.

🎙
> "An toàn thiết kế năm lớp: tự dừng trước vật cản, phát hiện nghiêng và va chạm, nút khẩn cấp vật lý, và watchdog — mất kết nối với Pi quá một giây, Arduino tự cắt động cơ."

---

## Cảnh 7 — Kết (2:50 – 3:00)

🎥 Xe chạy roam ở xa. 🖼 **Hình 5 — Card kết** đè lên 3 giây cuối.

🎙
> "Smart AI Car Plus — thị giác máy tính, hệ thống nhúng và web thời gian thực trong một sản phẩm hoàn chỉnh. Cảm ơn thầy cô và các bạn đã theo dõi."

---

## Mẹo dựng cho bản 3 phút

- Tổng lời thoại ~430 chữ — đọc tốc độ vừa là khớp 3:00; nếu đọc xong còn dư thì kéo dài cảnh demo AI, đừng kéo phần nói.
- Cắt hết khoảng chờ: đăng ký mặt, xe quay tìm marker — tua nhanh 2–4x, giữ nguyên tốc độ ở khoảnh khắc chính.
- Screen record web bằng OBS 1080p, đừng quay màn hình bằng điện thoại.
- Nhạc nền không lời, ~20% volume, chỉ nổi lên ở cảnh 1 và cảnh 7.
- Hình 2 và Hình 4 đứng yên hơi lâu sẽ chán — thu nhỏ dần (zoom out nhẹ 105%→100%) cho có chuyển động.
