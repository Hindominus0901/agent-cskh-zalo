# Giới hạn của Zalo Bot — đọc trước khi hứa với ai

Những giới hạn này đến từ **nền tảng Zalo**, không phải từ template. Không có
cách nào lập trình vòng qua.

> **Phần lớn chúng là giới hạn của Zalo Bot Creator, không phải của Zalo nói
> chung.** Zalo OA doanh nghiệp không bị mấy giới hạn này — nhưng nó là một sản
> phẩm khác, tốn công hơn hẳn. Xem
> [mục so sánh cuối `01-noi-zalo.md`](01-noi-zalo.md#khi-nào-bạn-buộc-phải-lên-oa).

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

Không có menu, không có nút "Xem bảng giá", không có nút "Đặt hàng". **Mọi tương
tác là chữ.**

Template này cố tình **không** bù bằng menu đánh số kiểu *"nhắn 1 để xem bảng giá"*.
Khách thật không đọc menu — họ gõ tiếp câu hỏi của mình, rồi con số lạc của lượt
trước làm bot mở nhầm một trang chẳng liên quan.

Thay vào đó, khi không chắc thì bot **đoán một cách thành thật**:

> Dạ có phải anh/chị đang hỏi về **Bảng giá** không ạ:
> …

Khách đọc dòng đầu là biết ngay có đúng ý mình không, và sửa được trong một lượt.

---

## 5. Tin nhắn tối đa 2.000 ký tự

Bot tự cắt thành nhiều tin. Nhưng bị cắt thì đọc rời rạc, nên tốt hơn là **viết
trang wiki ngắn** — mỗi trang trả lời đúng một câu hỏi.

Bot cắt phần thân trang ở 1.400 ký tự khi trả lời. Trang dài hơn thế thì phần sau
không bao giờ tới được khách. `scripts/wiki_index.py` sẽ cảnh báo.

---

## 6. Nhóm chat: được 3 nhóm, và bot chỉ nghe khi được gọi

**Đây thật ra là điểm MẠNH nhất của Bot Creator, không phải giới hạn** — Zalo OA
không vào được nhóm chat, chỉ Bot Creator vào được.

Cách thêm: mở mini app **Zalo Bot Creator**, chọn bot, thêm vào nhóm.

Trong nhóm, bot chỉ nghe khi được **@mention** hoặc khi có người **trả lời trực
tiếp** tin của bot. Nó không đọc toàn bộ chat nhóm — vừa riêng tư hơn, vừa đỡ tốn
hạn mức.

> **Cái bẫy hay gặp nhất:** gửi ảnh trong nhóm thì phải tag bot **ngay trong phần
> chú thích của chính tấm ảnh**. Tag ở tin trước rồi mới gửi ảnh ở tin sau thì bot
> **không nhận được ảnh** — và người ta tưởng bot hỏng.
> Xem [`06-dung-bot-tren-zalo.md`](06-dung-bot-tren-zalo.md).

Hợp với: lớp học, cộng đồng, nhóm khách VIP, nhóm nội bộ — chỗ cần một trợ lý
ngồi sẵn trả lời câu lặp đi lặp lại.

Giới hạn thật: **3 nhóm** ở gói Basic, và tính năng nhóm đang ở giai đoạn **beta**.

> ⚠️ Bot trong nhóm đọc được câu của mọi thành viên khi bị @mention. Đừng thêm bot
> vào nhóm mà bạn không muốn nó ghi lại nội dung — mọi câu hỏi nó không trả lời
> được đều được lưu vào báo cáo.

---

## 7. Không lấy được `chat_id` từ `user_id`

Zalo không cho tra ngược. Nghĩa là **bot không nhắn trước cho một người chưa từng
nhắn cho nó** — kể cả khi bạn biết số điện thoại của họ.

Đây là một trong những lý do template chưa làm chức năng nhắn chủ động.

---

## 8. Ảnh: URL hết hạn, và có giới hạn dung lượng

Zalo gửi ảnh cho bot dưới dạng **một đường link tạm**. Link đó **hết hạn**, nên
bot phải tải ảnh về ngay trong lượt đó — để lại link rồi mở sau là mở vào chỗ trống.

Bot đã làm đúng việc này (ảnh biên lai được tải về `data/media/`), nhưng nó giải
thích vì sao thư mục đó lớn dần và **bạn phải sao lưu nó** cùng với cơ sở dữ liệu.

Ảnh quá lớn (khoảng trên 5MB) có thể không tải về được. Dặn khách chụp bình
thường, đừng gửi ảnh gốc từ máy ảnh.

---

## 9. Tên bot bắt buộc bắt đầu bằng chữ "Bot"

Khi tạo trong Zalo Bot Creator, tên phải có tiền tố `Bot` — ví dụ `Bot Gác Nhỏ`.
Không có là không tạo được, và thông báo lỗi không nói rõ lý do.

Nghĩa là khách sẽ luôn nhìn thấy chữ "Bot" trong tên. Đặt tên sao cho nó tự
nhiên: `Bot Gác Nhỏ` đọc ổn hơn `Bot CSKH GN-2026`.

---

## Tóm lại — thiết kế cách làm việc quanh giới hạn

| Giới hạn | Cách sống chung |
|---|---|
| 3.000 tin/tháng | Viết trang wiki tốt để bot trả đúng ngay lượt đầu |
| Tắt máy mất tin | VPS nếu chạy thật |
| Không nhận file | Dặn khách chụp màn hình |
| Không có nút | Bot đoán thành thật (“có phải anh/chị hỏi về X không ạ”) |
| 2.000 ký tự | Trang ngắn, mỗi trang một câu hỏi |
| Trong nhóm phải @mention | Ghim hướng dẫn vào nhóm — có đoạn dán sẵn ở [06-dung-bot-tren-zalo.md](06-dung-bot-tren-zalo.md) |
