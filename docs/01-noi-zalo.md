# Đưa bot lên Zalo — từ A đến Z

Viết cho người chưa từng làm. Làm đúng thứ tự, đừng nhảy bước.

**Trước khi bắt đầu:** bot phải chạy được trong terminal đã. Chưa chạy được
`uv run agent-cskh chat` thì quay lại `HUONG-DAN-AGENT.md` — nối Zalo không sửa được vấn
đề của kho tri thức.

Tổng thời gian: khoảng 30 phút, **cộng thêm ~1 ngày chờ Zalo duyệt OA** ở bước 1.

---

## Bước 1 — Tạo Zalo OA (~1 ngày chờ duyệt)

Zalo Bot phải gắn vào một **Official Account**. Chưa có thì tạo trước.

1. Vào **https://oa.zalo.me** → *Tạo Official Account*
2. Chọn loại phù hợp (doanh nghiệp / cá nhân)
3. Điền thông tin và tải giấy tờ (CCCD hoặc giấy phép kinh doanh)
4. Chờ duyệt — thường trong vòng một ngày làm việc

Trong lúc chờ, cứ dùng `uv run agent-cskh chat` để hoàn thiện kho tri thức. Toàn
bộ công sức đó dùng lại được y nguyên.

---

## Bước 2 — Tạo bot và lấy token (~5 phút)

1. Vào **https://zalo.me/s/botcreator/**
2. Đăng nhập bằng tài khoản Zalo đang quản lý OA ở bước 1
3. Tạo bot mới, đặt tên và ảnh đại diện
4. Copy **token** — chuỗi có dạng `1234567890:AbCdEf...`

**Token này là chìa khoá vào bot của bạn.** Đừng gửi cho ai, đừng chụp màn hình
đăng lên nhóm, đừng commit lên GitHub.

---

## Bước 3 — Dán token vào máy (~2 phút)

Chưa có file `.env` thì tạo:

| Windows | macOS |
|---|---|
| `Copy-Item .env.example .env` | `cp .env.example .env` |

Mở `.env` bằng Notepad (Windows) hoặc TextEdit (macOS), tìm dòng:

```
ZALO_BOT_TOKEN=
```

Dán token vào ngay sau dấu `=`, **không có dấu cách, không có dấu ngoặc kép**:

```
ZALO_BOT_TOKEN=1234567890:AbCdEf...
```

Lưu lại.

---

## Bước 4 — Kiểm tra kết nối (~1 phút)

```bash
uv run agent-cskh check
```

Phải thấy dòng `[ok] ZALO_BOT_TOKEN có định dạng đúng`.

Báo sai định dạng thì kiểm lại: token phải có dấu hai chấm `:` ở giữa, và không
dính dấu cách thừa ở đầu hay cuối.

---

## Bước 5 — Chạy bot (~1 phút)

| Windows | macOS |
|---|---|
| `.\run.ps1` | `chmod +x run.sh` rồi `./run.sh` |

Thấy dòng `Bot: <tên bot> (id=...)` là đã kết nối được.

**Cứ để cửa sổ này mở.** Đóng nó là bot tắt.

---

## Bước 6 — Nhận quyền quản trị (~3 phút)

Bot đang chạy nhưng chưa biết bạn là chủ. Nó coi bạn như một khách lạ.

1. Mở Zalo trên điện thoại, tìm bot của bạn (tên đặt ở bước 2)
2. Nhắn cho bot: **`/whoami`**
3. Bot trả về `user_id` và `chat_id` của bạn
4. Copy `user_id`, mở lại `.env`, dán vào:

```
OWNER_USER_IDS=user_id_vua_copy
```

5. **Tắt bot (Ctrl+C) rồi chạy lại** — `.env` chỉ được đọc lúc khởi động
6. Nhắn `/whoami` lần nữa, giờ phải thấy `quyền hiện tại: owner`

---

## Bước 7 — Đặt kênh nhận cảnh báo (~1 phút)

Bot cần một chỗ để báo khi có khách đang chờ, hoặc khi nó gặp sự cố.

Trong **chat riêng** giữa bạn và bot, nhắn: **`/datkenhcanhbao`**

> ⚠️ **Đừng chạy lệnh này trong nhóm có khách hàng.** Nội dung cảnh báo kèm tên
> khách và `chat_id` của họ — chạy nhầm chỗ là bạn kể chuyện khách A cho khách B.

---

## Bước 8 — Thử bằng câu thật (~5 phút)

Nhắn cho bot **5 câu mà khách hay hỏi nhất**, đúng cách khách hay gõ (viết tắt,
không dấu, sai chính tả — cứ thử thật).

- Trả lời đúng → tốt
- Trả lời sai trang → thêm cách hỏi đó vào `tu_khoa` của trang đúng
- Nói "chưa nắm chắc" → kho thiếu trang đó, viết thêm

Sửa xong file thì nhắn **`/nap`** cho bot — nó nạp lại ngay, không cần khởi động lại.

---

## Bước 9 — Cho bot tự chạy mỗi khi bật máy (~2 phút)

| Windows | macOS |
|---|---|
| `.\scripts\cai_tu_khoi_dong.ps1` | `./scripts/cai_tu_khoi_dong.sh` |

---

## Sau đó

**Xem báo cáo:** nhắn `/baocao` bất cứ lúc nào, hoặc đợi báo cáo tự động 20h hàng
ngày. Mục *"câu bot KHÔNG trả lời được"* là danh sách việc cần làm — mỗi câu ở đó
là một trang cần viết.

**Sửa kho từ điện thoại:** `/dstrang`, `/xemtrang`, `/themtrang`, `/suatrang`.
Bản cũ luôn được giữ lại, sửa nhầm không mất.

**Xem còn bao nhiêu tin:** `/trangthai`.

---

## Chạy 24/7

Máy tính cá nhân tắt hoặc ngủ là bot dừng, và **tin nhắn gửi lúc đó mất hẳn** —
Zalo không lưu lại (xem [02-gioi-han-zalo.md](02-gioi-han-zalo.md)).

Muốn chạy thật lâu dài thì thuê VPS: [05-chuyen-len-vps.md](05-chuyen-len-vps.md).

---

## Gặp lỗi?

Xem [03-loi-hay-gap.md](03-loi-hay-gap.md) trước. Lỗi hay làm người ta hoảng nhất
— `error_code: 408` — **là bình thường**, không phải hỏng.
