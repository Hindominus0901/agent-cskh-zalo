# Đưa bot lên Zalo bằng Zalo Bot Creator — từ A đến Z

Viết cho người chưa từng làm. Làm đúng thứ tự, đừng nhảy bước.

**Trước khi bắt đầu:** bot phải chạy được trong terminal đã. Chưa chạy được
`uv run agent-cskh chat` thì quay lại `HUONG-DAN-AGENT.md` — nối Zalo không sửa
được vấn đề của kho tri thức.

Tổng thời gian: **khoảng 30 phút**, không phải chờ duyệt gì cả.

---

## Trước hết: Zalo có HAI loại bot khác nhau

Đây là chỗ làm nhiều người mất cả ngày vô ích, nên nói rõ ngay từ đầu.

| | **Zalo Bot Creator** ← template này dùng | Zalo OA (Official Account) |
|---|---|---|
| Tạo từ | Tài khoản Zalo cá nhân | Doanh nghiệp, cần giấy tờ |
| Chờ duyệt | Không | Có, thường ~1 ngày |
| Lấy token | Zalo nhắn tin cho bạn | Cổng developers.zalo.me |
| API | `bot-api.zaloplatforms.com` | `openapi.zalo.me` |

**Hai thứ này là hai sản phẩm riêng biệt**, không phải hai mức của cùng một thứ.
Template này chạy trên **Zalo Bot Creator**, và bạn **không cần OA doanh nghiệp**
để bắt đầu.

Nếu đọc ở đâu đó bảo "phải có OA đã" thì đó là hướng dẫn cho loại thứ hai.

---

## Bước 1 — Tạo bot trong ứng dụng Zalo (~5 phút)

Làm **trên điện thoại**, ngay trong app Zalo.

1. Mở Zalo, vào ô tìm kiếm, gõ **`Zalo Bot Manager`**
2. Mở Official Account đó (đây là OA của chính Zalo, không phải của bạn)
3. Trong khung chat, mở menu và chọn **"Tạo bot"** — nó bật lên ứng dụng
   **Zalo Bot Creator**
4. Điền thông tin bot:
   - **Tên bot phải bắt đầu bằng chữ `Bot`.** Ví dụ: `Bot Gác Nhỏ`,
     `Bot Shop Hoa`. Không có tiền tố này là không tạo được.
   - Ảnh đại diện, mô tả
5. Bấm **"Tạo Bot"**

---

## Bước 2 — Nhận token (~1 phút)

**Token KHÔNG hiện trên màn hình.** Zalo **nhắn tin cho bạn** — token nằm trong
tin nhắn từ Zalo Bot Manager trong chính Zalo của bạn.

Nó có dạng:

```
1234567890:AbCdEfGhIjKlMnOpQrStUvWxYz
```

Một dãy số, dấu hai chấm, rồi một chuỗi chữ.

> **Token này là chìa khoá vào bot của bạn.** Ai có nó thì nhắn được thay bạn và
> đọc được tin khách gửi. Đừng gửi cho ai, đừng chụp màn hình đăng lên nhóm,
> đừng dán vào chat với AI, đừng commit lên GitHub.
>
> Lỡ lộ thì vào Zalo Bot Creator thu hồi và cấp lại token mới — token cũ chết ngay.

Cách chuyển token từ điện thoại sang máy tính an toàn: tự nhắn cho chính mình
trong Zalo rồi mở Zalo trên máy tính mà copy. Đừng chụp màn hình gửi qua nhóm.

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
ZALO_BOT_TOKEN=1234567890:AbCdEfGhIjKlMnOpQrStUvWxYz
```

Lưu lại.

---

## Bước 4 — Kiểm tra kết nối (~1 phút)

```bash
uv run agent-cskh check
```

Phải thấy dòng `[ok] ZALO_BOT_TOKEN có định dạng đúng`.

Báo sai định dạng thì kiểm lại: token phải có dấu hai chấm `:` ở giữa, không
dính dấu cách thừa ở đầu hay cuối, và bạn copy **cả dãy** chứ không phải một nửa.

---

## Bước 5 — Chạy bot (~1 phút)

| Windows | macOS |
|---|---|
| `.\run.ps1` | `chmod +x run.sh` rồi `./run.sh` |

Thấy dòng `Bot: <tên bot> (id=...)` là đã kết nối được.

**Cứ để cửa sổ này mở.** Đóng nó là bot tắt.

Thấy `error_code: 408` chạy đi chạy lại thì **kệ nó** — đó là bình thường, không
phải lỗi. Xem [03-loi-hay-gap.md](03-loi-hay-gap.md).

---

## Bước 6 — Tìm bot của mình trong Zalo (~2 phút)

Bot vừa tạo không tự hiện trong danh bạ. Hai cách mở:

- Trong **Zalo Bot Creator**, mở bot của bạn, vào mục **Chia sẻ** — có sẵn một
  **Deeplink chính thức**. Bấm vào là mở chat với bot.
- Hoặc tìm theo tên bot trong ô tìm kiếm Zalo.

Nhắn thử một câu bất kỳ. Bot trả lời là xong phần kết nối.

---

## Bước 7 — Nhận quyền quản trị (~3 phút)

Bot đang chạy nhưng chưa biết bạn là chủ. Nó coi bạn như một khách lạ.

1. Nhắn cho bot: **`/whoami`**
2. Bot trả về `user_id` và `chat_id` của bạn
3. Copy `user_id`, mở lại `.env`, dán vào:

```
OWNER_USER_IDS=user_id_vua_copy
```

4. **Tắt bot (Ctrl+C) rồi chạy lại** — `.env` chỉ được đọc lúc khởi động
5. Nhắn `/whoami` lần nữa, giờ phải thấy `quyền hiện tại: owner`

---

## Bước 8 — Đặt kênh nhận cảnh báo (~1 phút)

Bot cần một chỗ để báo khi có khách đang chờ, hoặc khi nó gặp sự cố.

Trong **chat riêng** giữa bạn và bot, nhắn: **`/datkenhcanhbao`**

> ⚠️ **Đừng chạy lệnh này trong nhóm có khách hàng.** Nội dung cảnh báo kèm tên
> khách và `chat_id` của họ — chạy nhầm chỗ là bạn kể chuyện khách A cho khách B.

---

## Bước 9 — Thử bằng câu thật (~5 phút)

Nhắn cho bot **5 câu mà khách hay hỏi nhất**, đúng cách khách hay gõ (viết tắt,
không dấu, sai chính tả — cứ thử thật).

- Trả lời đúng → tốt
- Trả lời sai trang → thêm cách hỏi đó vào `tu_khoa` của trang đúng
- Nói "chưa nắm chắc" → kho thiếu trang đó, viết thêm

Sửa xong file thì nhắn **`/nap`** cho bot — nó nạp lại ngay, không cần khởi động
lại.

---

## Bước 10 — Cho bot tự chạy mỗi khi bật máy (~2 phút)

| Windows | macOS |
|---|---|
| `.\scripts\cai_tu_khoi_dong.ps1` | `./scripts/cai_tu_khoi_dong.sh` |

---

## Bảng điều khiển trong Zalo Bot Creator

Mở ứng dụng Zalo Bot Creator bất cứ lúc nào để xem:

| Tab | Có gì |
|---|---|
| **Thông tin** | Trạng thái bot, **Tổng số người dùng** đã tương tác |
| **Chia sẻ** | Deeplink chính thức để gửi cho khách |
| Cài đặt | Đổi tên, ảnh, thu hồi và cấp lại token |

**Mẹo chẩn đoán đáng giá:** nếu bot của bạn không nhận được tin nào mà
**"Tổng số người dùng" vẫn là 0** dù bạn đã nhắn cho nó nhiều lần — thì tin nhắn
không hề được gắn vào cuộc hội thoại nào ở phía Zalo. Lúc đó vấn đề nằm ở Zalo,
không phải ở máy bạn, và không có gì để sửa từ phía mình.

Chuyện này đã xảy ra thật ngày 05/08/2026: `getUpdates` trả 502/504 trên **mọi**
bot trong khoảng 2 tiếng rồi tự hồi phục.

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

---

## Nguồn và mức tin cậy

Tài liệu này ghép từ ba nguồn, và có chỗ chắc chắn hơn chỗ khác:

**Chắc chắn — đã chạy thật trên hệ thống:** đường API
`bot-api.zaloplatforms.com/bot<TOKEN>/<method>`, dạng token `số:chuỗi`, ý nghĩa
của `error_code: 408`, việc `getUpdates` không có `offset` (tắt máy là mất tin),
các tab trong Zalo Bot Creator, và sự cố 05/08/2026.

**Từ tài liệu chính thức của Zalo** ([bot.zapps.me/docs/create-bot](https://bot.zapps.me/docs/create-bot/)):
luồng tạo bot qua OA *Zalo Bot Manager*, quy tắc tên bot phải bắt đầu bằng `Bot`,
và việc token được gửi qua tin nhắn.

**Chưa tự kiểm chứng:** các bước bấm nút cụ thể trong ứng dụng Zalo Bot Creator —
giao diện có thể đã đổi. Nếu bạn thấy khác, sửa lại file này giúp.

Nguồn tham khảo:
- [Tài liệu Zalo Bot — Tạo Bot](https://bot.zapps.me/docs/create-bot/)
- [Zalo Bot Manager (OA của Zalo)](https://zalo.me/3899658094114941620)
- [OpenClaw — kênh Zalo](https://docs.openclaw.ai/channels/zalo)
