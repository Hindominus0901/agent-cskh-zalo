# Giới hạn của Zalo Bot — đọc trước khi hứa với ai

Những giới hạn này đến từ **nền tảng Zalo**, không phải từ template. Không có
cách nào lập trình vòng qua.

Biết trước thì thiết kế được cách làm việc quanh nó. Biết sau thì đã hứa với
khách mất rồi.

---

## 1. Hạn mức gói Basic

| | Giới hạn |
|---|---|
| Tin nhắn | **3.000 / tháng** |
| Người dùng | **50 / bot** |
| Nhóm | 3 (bản beta) |

**Đếm cả hai chiều** — tin khách gửi và tin bot trả đều tính. Một cuộc trò chuyện
qua lại 5 lượt tốn khoảng 10 tin.

3.000 tin ≈ **300 cuộc trò chuyện/tháng** ≈ 10 cuộc/ngày.

Bot tự cảnh báo khi dùng tới 80%, và tự dừng ở 95% để không bị Zalo khoá đột ngột.
Xem bất cứ lúc nào bằng cách nhắn *“còn bao nhiêu tin”*.

Gói Pro (129.000đ/tháng) vẫn đang "sắp ra mắt" — đã như vậy khá lâu.

---

## 2. Tắt máy là mất tin — giới hạn nặng nhất

Zalo **không lưu** tin nhắn gửi lúc bot offline. Không có cơ chế nhận bù về sau.

Nghĩa là: máy tắt, máy ngủ, mất mạng 10 phút, khởi động lại Windows — mọi tin
nhắn khách gửi trong khoảng đó **mất hẳn**, và bạn không bao giờ biết đã có ai
nhắn.

*(Kỹ thuật: `getUpdates` của Zalo không có tham số `offset`, nên việc nhận tin là
"nhiều nhất một lần" chứ không phải "ít nhất một lần" như Telegram.)*

**Hệ quả thực tế:**

- Chạy trên máy cá nhân chỉ hợp để **thử và học**
- Chạy thật với khách thật thì cần **VPS chạy 24/7** — xem
  [05-chuyen-len-vps.md](05-chuyen-len-vps.md)
- Trên macOS nhớ tắt chế độ ngủ, hoặc dùng `caffeinate`

---

## 3. Không gửi và nhận được file tài liệu

Khách gửi PDF, Word, Excel → **bot không nhận được gì cả**. Không phải bot không
đọc được, mà là Zalo không chuyển tới.

Bot cũng không gửi file đi được. Chỉ có: **chữ, ảnh, sticker**.

**Cách làm việc quanh nó:** dặn khách chụp màn hình gửi ảnh. Bot đọc được ảnh (ở
chế độ `ai`). Câu này đã có sẵn trong phần trợ giúp của bot.

---

## 4. Không có nút bấm

Không có menu, không có nút "Xem bảng giá", không có nút "Đặt hàng". Mọi tương
tác là **chữ** hoặc **lệnh `/`**.

Vì vậy khi bot cần khách chọn, nó đưa danh sách đánh số và mời khách **nhắn số**:

> Dạ anh/chị đang hỏi về ý nào ạ:
> 1. Bảng giá
> 2. Chính sách đổi trả

---

## 5. Tin nhắn tối đa 2.000 ký tự

Bot tự cắt thành nhiều tin. Nhưng bị cắt thì đọc rời rạc, nên tốt hơn là **viết
trang wiki ngắn** — mỗi trang trả lời đúng một câu hỏi.

Bot cắt phần thân trang ở 1.400 ký tự khi trả lời. Trang dài hơn thế thì phần sau
không bao giờ tới được khách. `scripts/wiki_index.py` sẽ cảnh báo.

---

## 6. Trong nhóm, bot chỉ nghe khi được @mention

Hoặc khi có người quote-reply tin của bot. Điều này đúng ra là tốt: bot không đọc
toàn bộ chat nhóm.

---

## 7. Không lấy được `chat_id` từ `user_id`

Zalo không cho tra ngược. Nghĩa là **bot không nhắn trước cho một người chưa từng
nhắn cho nó** — kể cả khi bạn biết số điện thoại của họ.

Đây là một trong những lý do template chưa làm chức năng nhắn chủ động.

---

## Tóm lại — thiết kế cách làm việc quanh giới hạn

| Giới hạn | Cách sống chung |
|---|---|
| 3.000 tin/tháng | Viết trang wiki tốt để bot trả đúng ngay lượt đầu |
| Tắt máy mất tin | VPS nếu chạy thật |
| Không nhận file | Dặn khách chụp màn hình |
| Không có nút | Danh sách đánh số, khách nhắn số |
| 2.000 ký tự | Trang ngắn, mỗi trang một câu hỏi |
