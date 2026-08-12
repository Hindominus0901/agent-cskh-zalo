# Nhúng bot lên website và landing page

Cùng con bot đó, cùng kho tri thức đó, nhưng ngồi ở góc phải trang web của bạn
thay vì trong Zalo. Khách không cần có Zalo, không cần bấm đi đâu cả.

```bash
uv run agent-cskh web
```

Mở `http://localhost:8080` là thấy bong bóng chat ở góc dưới bên phải.

---

## 1. Nhúng vào trang của bạn — một dòng

Dán trước thẻ `</body>`:

```html
<script src="https://bot.tenmiencuaban.com/widget.js" defer></script>
```

Tuỳ biến bằng thuộc tính `data-` ngay trên thẻ đó:

```html
<script src="https://bot.tenmiencuaban.com/widget.js"
        data-ten="Trợ lý Gác Nhỏ"
        data-mau="#e8542f"
        data-chao="Dạ em chào anh/chị, bên em giúp gì được ạ?"
        defer></script>
```

| Thuộc tính | Việc |
|---|---|
| `data-ten` | Tên hiện ở thanh tiêu đề |
| `data-mau` | Màu chủ đạo (mã màu của thương hiệu bạn) |
| `data-chao` | Câu chào đầu tiên |
| `data-goc="trai"` | Đổi sang góc trái |

Widget không tải thêm file nào, không dùng thư viện nào, và nằm trong Shadow DOM
nên **không bao giờ đá nhau với giao diện trang bạn**.

---

## 2. Bắt buộc: khai tên miền của bạn

Trình duyệt sẽ **chặn** widget nếu tên miền chưa được khai. Thêm vào `.env`:

```
WEB_ORIGINS=https://tenmiencuaban.com,https://www.tenmiencuaban.com
```

Ghi đủ cả `www` và không `www` nếu trang bạn dùng cả hai.

> Vì sao không để mặc định cho tất cả: mở cho cả internet nghĩa là **trang bất kỳ
> cũng nhúng được widget của bạn** rồi tính tiền API vào tài khoản của bạn.

---

## 3. Chọn chế độ — quan trọng hơn bạn nghĩ

| | `tra_cuu` (0 đồng) | `ai` |
|---|---|---|
| Chi phí mỗi lượt khách web | **0đ** | tiền thật |
| Rủi ro khi bị bot cào | không có gì để mất | **đốt sạch số dư** |
| Hợp với web công khai | **rất hợp** | cần cân nhắc |

Trên Zalo, nền tảng tự chắn hộ bạn: khách phải có tài khoản Zalo, gói Basic chỉ
50 người và 3.000 tin/tháng. **Website thì mở thẳng ra internet** — không đăng
nhập, không giới hạn người, và một con bot cào chạy cả đêm có thể tiêu hết tiền
API trước khi bạn ngủ dậy.

Nên **bắt đầu bằng `tra_cuu`**. Nó trả lời được phần lớn câu hỏi lặp đi lặp lại,
không bao giờ bịa, và không tốn đồng nào dù ai gõ bao nhiêu.

Muốn dùng `ai` trên trang công khai thì đọc kỹ mục 4.

---

## 4. Ba lớp chặn lạm dụng

Có sẵn, không phải bật:

| Lớp | Mặc định | Chặn gì |
|---|---|---|
| Nhịp theo IP | 10 lượt/phút | Người gõ dồn dập, script đơn giản |
| **Trần ngày** | **500 lượt/ngày** | **Trần cứng — thứ thật sự cứu tiền** |
| Trần chi phí ngày | 2 USD | Vượt thì tự hạ xuống model rẻ |

```
WEB_NHIP_IP_MOI_PHUT=10
WEB_TRAN_NGAY=500
DAILY_COST_LIMIT_USD=2
```

**Trần ngày là lớp quan trọng nhất.** Nhịp IP chỉ làm chậm kẻ phá — ai có sẵn
một dàn IP thì vượt qua được, và lúc đó chỉ còn trần ngày dừng lại. Nó đếm **cả
lượt bị từ chối**, nếu không kẻ bị chặn vẫn thử lại vô hạn mà không bao giờ chạm
trần.

Chạm trần thì bot ngừng phục vụ **web** đến hôm sau — **Zalo vẫn chạy bình thường**.

Xem còn bao nhiêu bất cứ lúc nào:

```bash
curl https://bot.tenmiencuaban.com/health
```

---

## 5. Khách web là người lạ — vĩnh viễn

Trên Zalo, `user_id` do Zalo cấp nên hệ phân quyền tin được. Trên web thì
"danh tính" chỉ là một cookie bạn tự phát — khách **xoá cookie là thành người
mới**, và sửa được.

Vì vậy khách web **luôn** ở vai `stranger`:

- chỉ đọc được `knowledge/wiki/public/`
- **không bao giờ** chạm tới `wiki/internal/` (giá vốn, quy trình nội bộ)
- không có đường nào nâng quyền từ web

Nghe như hạn chế, nhưng đó là câu trả lời đúng. **Việc quản trị vẫn làm trong
Zalo** — nơi danh tính là thật.

---

## 6. Cái bẫy lớn nhất: khách web đóng tab là mất

Trên Zalo, tư vấn viên nhắn lại được, khách thấy tin đó kể cả vài tiếng sau.
**Trên web không có gì như vậy.** Đóng tab là không còn đường nào tới khách.

Nên khi bot phải chuyển người thật, ở web nó **không hứa "mình chờ giúp em"** —
nó xin một đường liên lạc thật:

> Dạ em đã ghi nhận và báo cho anh/chị phụ trách rồi ạ. Anh/chị để lại số điện
> thoại hoặc Zalo giúp em để bên em liên hệ lại nhé — vì ở đây sau khi mình đóng
> trang thì em không nhắn lại được ạ.

**Và bạn nên khai `ZALO_BOT_TOKEN` ngay cả khi chỉ chạy web.** Kênh web tự nó
không báo được cho ai — cảnh báo *"có khách đang chờ người"* đi qua Zalo. Không
có token thì bot vẫn chạy, nhưng **bạn sẽ không biết có khách nào cần bạn**, và
lúc khởi động nó sẽ nói thẳng điều đó.

---

## 7. Đưa lên mạng thật

Mặc định máy chủ **chỉ nghe ở máy bạn** (`127.0.0.1`) — đúng như vậy khi đang thử.

Chạy thật thì phải có **HTTPS**, vì cookie phiên đi qua đường đó. Cách gọn nhất
là đặt Caddy đứng trước:

```
bot.tenmiencuaban.com {
    reverse_proxy 127.0.0.1:8080
}
```

Caddy tự xin chứng chỉ. Rồi đổi `.env`:

```
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_ORIGINS=https://tenmiencuaban.com
```

> **Đừng phơi thẳng cổng 8080 ra internet.** Không có HTTPS thì cookie phiên đi
> qua đường không mã hoá.

Máy chủ cần chạy 24/7 y như bot Zalo — xem
[`07-cho-bot-chay-24-7.md`](07-cho-bot-chay-24-7.md).

---

## 8. Chạy cả web lẫn Zalo cùng lúc

Được, và nên. Hai tiến trình riêng, **dùng chung một kho tri thức và một cơ sở
dữ liệu**:

```bash
uv run agent-cskh chay    # Zalo
uv run agent-cskh web     # website
```

Sửa một trang wiki là **cả hai** cùng biết.

Lưu ý: các việc định kỳ (báo cáo 20h, cảnh báo hạn mức, nhắc handoff) nằm ở tiến
trình **Zalo**. Chạy mỗi web thì không có báo cáo hàng ngày.

---

## 9. Những gì kênh web CHƯA làm được

Nói trước để bạn không hứa với khách:

- **Không nhận ảnh.** Khách gửi ảnh biên lai thì phải qua Zalo. Widget hiện chỉ có chữ.
- **Không nhắn trước.** Không có "bot chào khách sau 30 giây trên trang".
- **Không có lịch sử xuyên thiết bị.** Cookie theo trình duyệt: khách mở trên
  điện thoại là một phiên khác.
- **Không có ô để nhân viên trả lời trực tiếp.** Tiếp quản vẫn làm trong Zalo.

---

## Đọc tiếp

- [`07-cho-bot-chay-24-7.md`](07-cho-bot-chay-24-7.md) — cho máy chủ sống 24/7
- [`04-bon-tru-cot.md`](04-bon-tru-cot.md) — bot trả lời sai thì sửa ở đâu
- [`02-gioi-han-zalo.md`](02-gioi-han-zalo.md) — giới hạn bên Zalo
