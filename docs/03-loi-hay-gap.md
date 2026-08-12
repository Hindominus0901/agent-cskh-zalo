# Lỗi hay gặp

---

## `error_code: 408` — KHÔNG PHẢI LỖI

Đây là thứ làm người ta hoảng nhiều nhất, nên để lên đầu.

```
zalo_api_error  code=408  method=getUpdates
```

Nghĩa là: **bot hỏi Zalo "có tin mới không", chờ 30 giây, không có ai nhắn cả.**
Bot hỏi lại. Bình thường hoàn toàn.

Bot đang chạy tốt mà không có khách nhắn thì bạn sẽ thấy dòng này khoảng hai phút
một lần, mãi mãi. **Cứ để yên.**

---

## `ModuleNotFoundError: No module named 'anthropic.types.beta.beta_managed_agents_...'`

Hoặc bất kỳ `ModuleNotFoundError` nào trỏ vào một file có **tên rất dài** bên
trong `.venv`.

**Không phải thiếu thư viện.** Đây là giới hạn 260 ký tự đường dẫn của Windows.
`uv sync` báo cài thành công, nhưng Python không mở nổi file có đường dẫn quá dài.

Kiểm tra:

```powershell
(Get-Location).Path.Length
```

Trên 130 là nguy hiểm. Cách sửa duy nhất chắc chắn: **chuyển cả thư mục dự án ra
chỗ ngắn hơn**, ví dụ `C:\agent-cskh`, rồi chạy lại `uv sync`.

Hay dính khi clone vào `Documents\OneDrive\Dự án của tôi\...` — mỗi cấp thư mục
tiếng Việt ăn thêm chục ký tự.

*(macOS không có vấn đề này.)*

`uv run agent-cskh check` sẽ cảnh báo trước khi bạn dính lỗi này.

---

## `Khong xac thuc duoc voi Zalo`

Token sai. Kiểm theo thứ tự:

1. Token có dấu hai chấm `:` ở giữa không? Đúng dạng: `1234567890:AbCdEf...`
2. Có dấu cách thừa ở đầu hoặc cuối không?
3. Có lỡ để dấu ngoặc kép không? `.env` **không dùng** dấu ngoặc kép.
4. Đã thu hồi và cấp lại token trong Zalo Bot Creator mà quên cập nhật `.env`?

Sửa `.env` xong phải **tắt bot rồi chạy lại** — file chỉ được đọc lúc khởi động.

---

## Bot không trả lời gì cả trên Zalo

Kiểm lần lượt:

1. Cửa sổ chạy bot còn mở không? Đóng là bot tắt.
2. Có thấy dòng `Bot: <tên> (id=...)` lúc khởi động không?
3. Nhắn *“id của tôi”* — bot trả lời thì nó đang sống, vấn đề nằm ở kho tri thức.
4. Nhắn trong **nhóm** thì phải @mention bot mới nghe.

---

## Bot bảo "em chưa nắm chắc" cho câu mà kho ĐÃ có

Gần như luôn là do **thiếu `tu_khoa`**.

Ở chế độ `tra_cuu`, tìm kiếm là khớp từ. Trang tiêu đề "Bảng giá" sẽ trượt khi
khách gõ *"mắc không"*, *"bao nhiêu xu"*, *"tầm nhiêu"* — vì không có chữ nào
trùng.

Sửa: mở trang đó, thêm vào frontmatter đúng cách khách vừa hỏi:

```yaml
tu_khoa: ["bao nhieu tien", "gia", "mac khong", "tam nhieu", "co dat khong"]
```

Rồi nhắn *“nạp lại kho”* cho bot.

**Cách lấy `tu_khoa` cho đúng:** mở lại tin nhắn khách cũ và chép nguyên văn.
Đừng ngồi nghĩ ra.

---

## Bot trả lời sai trang

Hai trang đang "tranh nhau" cùng một từ khoá.

1. Chạy `uv run agent-cskh chat`, gõ đúng câu đó, xem nó ra trang nào
2. Bỏ từ khoá bị trùng khỏi trang sai
3. Thêm từ khoá đặc trưng hơn cho trang đúng

Hoặc bot đang hỏi lại *"anh/chị hỏi về ý nào ạ"* — nghĩa là điểm hai trang sát
nhau. Đó là hành vi đúng, không phải lỗi.

---

## `uv: command not found` / `uv khong duoc nhan dien`

Chưa cài `uv`, hoặc đã cài nhưng terminal chưa nhận.

| Windows | macOS |
|---|---|
| `winget install astral-sh.uv` | `brew install uv` |

Cài xong **đóng terminal và mở lại**.

---

## `./run.sh: Permission denied` (macOS)

```bash
chmod +x run.sh
```

---

## Bot đang chạy nhưng sửa file wiki mà không thấy đổi

Nhắn **“nạp lại kho”** cho bot. Nó nạp lại ngay, không cần khởi động lại.

Sửa `persona.md` hoặc `.env` thì **phải khởi động lại** — hai file đó chỉ đọc lúc
bot khởi động.

---

## `agent-cskh check` báo `persona.md còn N chỗ [CHỜ HỌC VIÊN]`

Coding agent chưa phỏng vấn xong, hoặc đã phỏng vấn mà chưa điền hết.

Mở `knowledge/persona.md`, tìm chữ `[CHỜ HỌC VIÊN`, điền câu trả lời thật của bạn
vào. **Đừng để agent tự bịa** — đó chính là thứ dấu này ngăn.

---

## Zalo trả 502 / 504 liên tục cho mọi lệnh

Nếu **mọi** lệnh đều lỗi, kể cả `getMe`, và tình trạng kéo dài hơn 15 phút — nhiều
khả năng là **hạ tầng Zalo đang có sự cố**, không phải máy bạn.

Đã từng xảy ra: ngày 05/08/2026, `getUpdates` chết khoảng 2 tiếng trên mọi bot rồi
tự hồi phục.

Cách kiểm nhanh: tạo một bot thứ hai trong Zalo Bot Creator với token mới, chạy thử. Cùng
lỗi → không phải do bạn. Cứ chờ.

---

## Bot xác nhận nhầm một điều nó không được phép

Ví dụ nói "đã nhận được tiền", hoặc báo một con số giá không có trong kho.

**Đây là chuyện nghiêm trọng, không phải phiền toái.** Bot có lớp chặn cho đúng
hai việc này, và nó sẽ gửi cảnh báo cho bạn khi chặn được.

Nếu một câu như vậy vẫn lọt tới khách:

1. Chụp lại nguyên văn
2. Kiểm `knowledge/persona.md` còn mục *"Xác nhận đã nhận tiền"* và *"KHÔNG báo
   giá"* không — ai đó có thể đã xoá khi viết lại persona
3. Chạy `uv run pytest tests/test_authz.py -q`

Test `TestPersonaCoDuThanhPhan` sinh ra đúng để bắt trường hợp này.
