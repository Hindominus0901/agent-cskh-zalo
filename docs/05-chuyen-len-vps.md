# Chuyển lên VPS chạy 24/7

Chạy trên máy Windows thì **tắt máy là bot chết, và tin nhắn gửi trong lúc đó mất
hẳn** — `getUpdates` của Zalo không có `offset`, họ không lưu lại tin để giao sau.
Đó là lý do duy nhất cần VPS. Mọi thứ khác chạy tốt trên máy local.

---

## Cần gì

| | |
|---|---|
| VPS | 1 CPU, 1 GB RAM là dư. Ubuntu 22.04 hoặc 24.04. |
| Tên miền | Chỉ cần khi chạy webhook. Polling thì không cần gì. |
| Chi phí tham khảo | VPS Việt Nam 100–200k/tháng; Hetzner/DigitalOcean ~$5/tháng |

Đặt VPS ở Singapore hoặc Việt Nam — gần Zalo, độ trễ thấp hơn.

---

## Chọn polling hay webhook

| | Polling | Webhook |
|---|---|---|
| Tên miền | Không cần | **Bắt buộc**, phải HTTPS |
| Độ trễ | Vài giây | Tức thì |
| Tải | Gọi Zalo liên tục | Chỉ khi có tin |
| Rủi ro đã gặp | `getUpdates` từng chết 2 tiếng ngày 05/08/2026 | Zalo gọi tới, ta chỉ chờ |

**Bắt đầu bằng polling.** Không cần tên miền, chuyển sang webhook sau chỉ là đổi
một dòng trong `.env`. Chuyển khi nào bạn thấy độ trễ vài giây là vấn đề, hoặc khi
lượng tin đủ lớn để việc gọi liên tục thành lãng phí.

---

## Các bước

### 1. Cài Docker trên VPS

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Đăng xuất rồi đăng nhập lại cho quyền có hiệu lực.

### 2. Đưa mã nguồn lên

```bash
git clone <repo-cua-ban> /opt/agent-cskh
cd /opt/agent-cskh
```

Chưa đẩy lên Git thì nén từ máy Windows rồi chép sang:

```powershell
# Trên máy Windows — KHÔNG kèm .env, data, secrets
tar -czf agent-cskh.tar.gz --exclude=.venv --exclude=data --exclude=.env --exclude=secrets .
scp agent-cskh.tar.gz user@vps:/opt/
```

### 3. Tạo `.env` trên VPS

**Không chép `.env` từ máy Windows sang.** Tạo mới và dán khoá vào:

```bash
cp .env.example .env
nano .env
```

Điền `ZALO_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `OWNER_USER_IDS`, `ALERT_CHAT_ID`.
Để `TRANSPORT=polling`.

```bash
chmod 600 .env
```

### 4. Chép kho tri thức lên

```powershell
scp -r knowledge user@vps:/opt/agent-cskh/
```

Không chép `data/` — để bot tự tạo CSDL mới. Muốn giữ lịch sử hội thoại và lead cũ
thì chép cả `data/app.db`.

### 5. Chạy

```bash
docker compose up -d
docker compose logs -f
```

Thấy `polling_bat_dau` là xong. Nhắn cho bot từ điện thoại để xác nhận.

---

## Chọn vùng đặt máy: Singapore

Đây là quyết định hay bị bỏ qua và không sửa lại được sau khi đã dựng.

Zalo đặt máy chủ ở Việt Nam. Từ VPS Singapore ping tới đó khoảng **30–50ms**;
từ Mỹ hoặc châu Âu là **200ms+**. Một lượt trả lời có thể chạy tới 8 vòng gọi
model và công cụ, nên con số đó nhân lên thành thứ khách cảm nhận được.

Bậc miễn phí của Google Compute Engine (`e2-micro`) chỉ có ở vùng Mỹ. Rẻ hơn
nhưng chậm hơn ở đúng chỗ khách nhìn thấy.

**1 GB RAM · 1 vCPU · 25 GB đĩa** là dư. Bot cần ~200 MB, log tự xoay vòng ở
trần 60 MB (10 MB × 6 file), và toàn bộ venv chỉ 81 MB.

---

## Chuyển sang webhook

**Ở mức 50 khách/tháng — trần của gói Basic — thì chưa cần.** Polling không mở cổng nào ra internet — bề mặt
tấn công từ ngoài bằng 0 — và webhook chỉ nhanh hơn 1–2 giây. Đọc mục này khi
thật sự cần độ trễ thấp, đừng làm vì nó "chuyên nghiệp hơn".

Có hai đường. **Cloudflare Tunnel đơn giản và an toàn hơn** cho trường hợp này.

### Đường A — Cloudflare Tunnel (khuyên dùng)

Không mở cổng nào, không cần IP tĩnh, không mua chứng chỉ. VPS chỉ **gọi ra**;
Cloudflare giữ đầu kia và chuyển tiếp vào.

Cần: một tên miền đã trỏ nameserver về Cloudflare (gói miễn phí là đủ).

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb && sudo dpkg -i cloudflared.deb
```

```bash
cloudflared tunnel login
```

```bash
cloudflared tunnel create zalo-bot
```

```bash
cloudflared tunnel route dns zalo-bot bot.tenmiencuaban.com
```

Tạo `/etc/cloudflared/config.yml`:

```yaml
tunnel: zalo-bot
credentials-file: /root/.cloudflared/<UUID>.json
ingress:
  - hostname: bot.tenmiencuaban.com
    service: http://127.0.0.1:8080
  # Bắt buộc phải có dòng cuối này. Thiếu nó thì mọi hostname khác cũng lọt vào bot.
  - service: http_status:404
```

```bash
sudo cloudflared service install && sudo systemctl status cloudflared
```

Rồi làm tiếp bước 3 và 4 bên dưới. **Đóng luôn cổng vào** — tunnel không cần:

```bash
sudo ufw allow 22/tcp && sudo ufw deny 8080/tcp && sudo ufw enable
```

**Đừng bật Cloudflare Access lên đường `/webhook`.** Access chèn một trang đăng
nhập, và Zalo không đăng nhập được — webhook sẽ chết im lặng.

### Đường B — Caddy (khi không dùng Cloudflare)

Cần IP tĩnh và mở cổng 443 ra internet.

#### Trỏ tên miền về IP của VPS

Bản ghi A: `bot.tenmiencuaban.com` → IP VPS.

#### Cài Caddy làm reverse proxy

Caddy tự xin và tự gia hạn chứng chỉ HTTPS, không phải cấu hình gì thêm:

```bash
sudo apt install -y caddy
sudo nano /etc/caddy/Caddyfile
```

```
bot.tenmiencuaban.com {
    reverse_proxy 127.0.0.1:8080
}
```

```bash
sudo systemctl restart caddy
```

### Chung cho cả hai đường — đổi `.env`

```
TRANSPORT=webhook
WEBHOOK_URL=https://bot.tenmiencuaban.com
WEBHOOK_SECRET=<chuỗi ngẫu nhiên 32 ký tự>
```

Sinh secret:

```bash
openssl rand -base64 24
```

### Chung cho cả hai đường — khởi động lại

```bash
docker compose restart
```

Bot tự gọi `setWebhook` lúc khởi động. Kiểm tra:

```bash
curl https://bot.tenmiencuaban.com/health
```

---

## Vận hành

| Việc | Lệnh |
|---|---|
| Xem log | `docker compose logs -f --tail=100` |
| Khởi động lại | `docker compose restart` |
| Cập nhật mã | `git pull && docker compose up -d --build` |
| Sửa kho tri thức | Sửa file trong `knowledge/` rồi nhắn “nạp lại kho” cho bot |
| Sao lưu | `docker compose exec bot python scripts/sao_luu.py` |
| Xem báo cáo | Nhắn “báo cáo hôm nay” cho bot, hoặc đợi báo cáo tự động 20:00 |

Bot tự khởi động lại khi VPS reboot nhờ `restart: unless-stopped`.

### Xem bot còn thiếu gì

Không cần vào VPS. Nhắn **“báo cáo hôm nay”** cho bot ngay trong Zalo — mục *"câu bot
KHÔNG trả lời được"* là danh sách trang cần viết thêm, đã gom theo số người hỏi.

Bot cũng tự gửi báo cáo này lúc 20:00 hằng ngày về kênh cảnh báo.

### Sao lưu tự động

**KHÔNG dùng `cp`.** Cơ sở dữ liệu chạy WAL: phần ghi mới nhất nằm trong
`app.db-wal` chứ chưa vào `app.db`. `cp` chỉ lấy file chính và cho ra một bản
sao **thiếu dữ liệu gần nhất** — mà lại trông hoàn toàn bình thường, nên không
ai phát hiện cho tới lúc cần phục hồi.

`scripts/sao_luu.py` dùng `sqlite3.backup()` — API chính thức, gộp cả WAL, chạy
được ngay khi bot đang ghi.

```bash
crontab -e
```

```
0 2 * * * cd /opt/agent-cskh && docker compose exec -T bot python scripts/sao_luu.py >> data/logs/sao-luu.log 2>&1
```

Kho tri thức đã nằm trong git nên không cần sao lưu riêng — nhưng **repo phải là
private**: `knowledge/wiki/internal/` chứa tài liệu nội bộ và bộ tiêu chí chấm.

---

## Những chỗ dễ vấp

**Chép nguyên `.env` từ Windows sang.** Nó chứa `TRANSPORT=polling` và `WEBHOOK_URL`
trỏ về đường hầm tạm đã chết. Tạo file mới.

**Quên `chmod 600 .env`.** File chứa khoá API tiêu tiền thật.

**Chạy hai bản cùng lúc.** Nếu máy Windows vẫn đang chạy bot mà VPS cũng chạy, hai
tiến trình sẽ giành nhau `getUpdates` và tin nhắn bị chia ngẫu nhiên giữa hai bên.
**Tắt bản trên Windows trước:**

```powershell
Stop-ScheduledTask -TaskName ZaloAgentBot
.\scripts\cai_tu_khoi_dong.ps1 -Go
```

**Sai múi giờ.** Dockerfile đặt sẵn `TZ=Asia/Ho_Chi_Minh`. Nếu log hiện giờ UTC thì
kiểm tra biến đó còn không.

**Webhook không nhận được gì.** Kiểm tra theo thứ tự: `curl` tới `/health` từ ngoài
Internet có thông không → `getWebhookInfo` có trỏ đúng URL không → log Caddy có thấy
request từ Zalo không. Nếu cả ba đều ổn mà vẫn không có tin, xem `docs/04-van-hanh.md`
— đã có tiền lệ hạ tầng Zalo chết chứ không phải lỗi mình.
