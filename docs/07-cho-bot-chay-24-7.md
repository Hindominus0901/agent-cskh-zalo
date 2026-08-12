# Cho bot chạy thật 24/7

Bot đã trả lời được trên Zalo. Nhưng bạn vẫn đang chạy nó bằng một cửa sổ terminal
mở trên máy mình — **đóng cửa sổ đó là bot chết.**

Tài liệu này trả lời câu tiếp theo: *chạy nó ở đâu để nó sống mãi?*

---

## Vì sao chuyện này quan trọng hơn bạn nghĩ

Bot tắt không chỉ là "khách phải chờ". **Tin nhắn gửi lúc bot tắt là mất hẳn.**

Zalo không lưu lại và không gửi bù. Bật máy lên, bot không hề biết đã có ai nhắn —
và bạn cũng không. Không có thông báo, không có dấu vết, không có cách nào biết
mình vừa mất mấy khách.

*(Kỹ thuật: `getUpdates` của Zalo không có `offset` — xem
[`02-gioi-han-zalo.md`](02-gioi-han-zalo.md).)*

Nên câu hỏi không phải "bot có chạy không" mà là **"bot có bao giờ tắt không"**.

---

## Tin tốt: bạn KHÔNG cần domain, IP tĩnh hay HTTPS

Template chạy chế độ **polling** mặc định — bot **gọi ra** Zalo để hỏi có tin mới
không. Zalo không cần gọi ngược vào máy bạn.

Nghĩa là bạn **không cần**: tên miền, IP tĩnh, chứng chỉ SSL, Cloudflare, mở cổng
tường lửa. Chỉ cần **một cái máy có mạng và không tắt**.

Đây là lý do phần triển khai đơn giản hơn nhiều so với vẻ ngoài của nó.

---

## Ba lựa chọn

| | Tiền/tháng | Công sức | Hợp khi |
|---|---|---|---|
| **A. Máy cá nhân** | 0đ | 5 phút | Đang thử, ít khách, chấp nhận thỉnh thoảng mất tin |
| **B. VPS** | ~50–150k | 1–2 giờ lần đầu | **Chạy thật với khách thật** |
| **C. Máy cũ ở nhà** | ~20k tiền điện | 30 phút | Có sẵn máy cũ, mạng nhà ổn định |

Nếu bot đang phục vụ khách thật và bạn quan tâm tới doanh thu từ nó, câu trả lời
gần như luôn là **B**.

---

## A. Chạy trên máy cá nhân (0 đồng)

Hợp để **thử và học**, không hợp để chạy thật.

### Cài tự khởi động

| Windows | macOS |
|---|---|
| `.\scripts\cai_tu_khoi_dong.ps1` | `./scripts/cai_tu_khoi_dong.sh` |

Từ đó mỗi lần bật máy là bot tự chạy, không cần mở terminal.

### Bắt buộc: tắt chế độ ngủ

Đây là bước ai cũng quên, và nó làm hỏng cả việc.

**Máy ngủ = bot tắt = mất tin.** Cài tự khởi động không cứu được, vì máy có tắt
hẳn đâu — nó chỉ ngủ.

- **Windows:** Cài đặt → Hệ thống → Nguồn & pin → Màn hình và chế độ ngủ →
  đặt **"Không bao giờ"** cho mục ngủ. Laptop thì đặt cho cả khi cắm điện.
- **macOS:** Cài đặt → Tiết kiệm năng lượng → bật *"Ngăn máy Mac tự động ngủ"*.
  Hoặc chạy `caffeinate -i ./run.sh`.

### Biết trước những gì sẽ mất

- Mất mạng vài phút → mất tin trong khoảng đó
- Windows tự cập nhật rồi khởi động lại lúc 3h sáng → mất tin
- Mang laptop đi họp → bot tắt cả buổi
- Cúp điện → mất tin

Chấp nhận được khi đang thử. Không chấp nhận được khi khách đang chờ trả lời.

---

## B. VPS — cách duy nhất thật sự ổn

Một máy chủ nhỏ chạy liên tục. **Không cần domain**, chỉ cần máy có mạng.

### Chọn máy thế nào

- **Cấu hình:** 1 GB RAM là đủ. Template không dùng vector database nên nhẹ.
- **Vùng đặt:** **Singapore** cho độ trễ tốt với Việt Nam, hoặc VPS trong nước.
- **Giá:** khoảng 50–150k/tháng tuỳ nhà cung cấp.

### Các bước

Toàn bộ quy trình có ở [`05-chuyen-len-vps.md`](05-chuyen-len-vps.md). Tóm tắt:

1. Cài Docker trên VPS
2. Đưa mã nguồn lên (`git clone`, hoặc nén rồi chép — **không kèm `.env`**)
3. **Tạo `.env` mới ngay trên VPS** và tự gõ lại token vào đó
4. Chép `knowledge/` lên
5. `docker compose up -d`

> **Bỏ qua toàn bộ phần "Chuyển sang webhook"** trong tài liệu đó, trừ khi bạn
> thật sự cần. Với polling thì bạn không cần Cloudflare Tunnel, không cần Caddy,
> không cần tên miền. Phần đó chiếm gần một nửa tài liệu và phần lớn người dùng
> không bao giờ đụng tới.

### Đừng chép `.env` từ máy mình lên

Tạo mới trên VPS rồi tự gõ token vào. `.env` đi qua email, chat hay ổ cứng chung
là token có thêm một chỗ để rò.

```bash
chmod 600 .env
```

---

## C. Máy cũ ở nhà

Một laptop cũ hay máy mini để ở góc nhà, cắm điện, nối mạng.

Cùng cách làm với A (tự khởi động + tắt ngủ), nhưng máy đó **không dùng vào việc
gì khác** nên không ai đóng nhầm, không ai mang đi.

Điểm yếu: mất điện hoặc mất mạng nhà thì bot tắt, và bạn thường không biết ngay.

---

## Bảng kiểm trước khi coi là "chạy thật"

Đánh dấu hết rồi hãy phát link bot cho khách:

- [ ] Bot tự khởi động lại khi máy khởi động
- [ ] Máy **không bao giờ ngủ**
- [ ] `.env` trên máy chạy có `chmod 600`, và **không** nằm trong git
- [ ] Đã đặt kênh cảnh báo (nhắn *"đặt kênh cảnh báo"* trong chat riêng với bot)
- [ ] Đã thử tắt bot rồi bật lại — nó tự lên
- [ ] Đã hẹn lịch sao lưu (xem dưới)
- [ ] Kho tri thức có ít nhất 5 trang và `agent-cskh check` xanh hết

---

## Làm sao biết bot còn sống

Bot **tự canh chính nó**:

- Zalo im lặng quá 10 phút → bot nhắn cho bạn qua kênh cảnh báo
- Model lỗi 3 lượt liên tiếp → bot nhắn cho bạn
- 9h sáng: cảnh báo nếu hạn mức tháng đã dùng quá 80%
- 20h: báo cáo hàng ngày

**Nhưng bot chết hẳn thì nó không tự báo được** — không có gì chạy để mà báo.

Cách kiểm rẻ nhất: mỗi sáng nhắn cho bot một câu bất kỳ. Không trả lời trong một
phút là có chuyện.

---

## Sao lưu — thứ hay bỏ quên nhất

```bash
uv run python scripts/sao_luu.py
```

Nó chép ba thứ, và cả ba đều **không mua lại được bằng tiền**:

- **`knowledge/`** — công sức phỏng vấn và viết trang. Mất là làm lại từ đầu.
- **`data/app.db`** — lịch sử hội thoại, lead khách để lại, biên lai chờ đối soát.
- **`data/media/`** — ảnh chuyển khoản đã tải về. Link gốc của Zalo **đã hết hạn**,
  nên mất file là mất luôn bằng chứng.

Hẹn lịch chạy hằng ngày, và **để bản sao ở một chỗ khác** — sao lưu nằm cùng máy
với dữ liệu thì cùng chết một lúc.

`knowledge/` được git theo dõi, nên nếu bạn đã đẩy lên GitHub (repo **private**)
thì nó đã có một bản ở nơi khác rồi.

---

## Cập nhật bot sau này

Sửa kho tri thức thì **không cần** làm gì với máy chủ — nhắn *"nạp lại kho"* cho bot.

Sửa `persona.md` hoặc `.env` thì phải khởi động lại:

```bash
docker compose restart
```

Lấy bản mã nguồn mới:

```bash
git pull && docker compose up -d --build
```

---

## Đọc tiếp

- [`05-chuyen-len-vps.md`](05-chuyen-len-vps.md) — quy trình VPS đầy đủ
- [`03-loi-hay-gap.md`](03-loi-hay-gap.md) — `error_code: 408` là bình thường
- [`06-dung-bot-tren-zalo.md`](06-dung-bot-tren-zalo.md) — đưa bot cho khách và cho nhóm
