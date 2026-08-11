# AI Agent chăm sóc khách hàng trên Zalo

Template để bạn dựng con bot CSKH của **chính doanh nghiệp mình** — trả lời khách
trên Zalo bằng đúng thông tin của bạn, và biết im lặng chuyển cho người thật khi
nó không chắc.

**Bạn không cần biết lập trình.** Đưa link repo này cho một coding agent (Claude
Code, Cursor, Codex), nó sẽ đọc `HUONG-DAN-AGENT.md`, phỏng vấn bạn, rồi dựng xong.

---

## Ba bước

**1. Tải về**

```bash
git clone <link-repo-cua-ban>
```

**2. Mở thư mục vừa tải bằng Claude Code, Codex hoặc Cursor, rồi gõ đúng câu này:**

> Đọc HUONG-DAN-AGENT.md và dựng bot cho tôi.

Dùng công cụ nào cũng được — cả ba đều dẫn về cùng một hướng dẫn. Chi tiết cho
từng công cụ: [docs/00-cai-dat.md](docs/00-cai-dat.md).

Nó sẽ hỏi bạn khoảng 17 câu về doanh nghiệp — bán gì, khách hay hỏi gì, giá thế
nào, điều gì bot tuyệt đối không được nói. **Trả lời thật, đừng trả lời cho có:**
bot chỉ biết đúng những gì bạn kể.

**3. Thử ngay trong máy**

```bash
uv run agent-cskh chat
```

Gõ vài câu như một khách hàng. Chưa cần Zalo, chưa cần trả tiền gì cả.

Muốn đưa lên Zalo thật thì mở [docs/01-noi-zalo.md](docs/01-noi-zalo.md).

---

## Hai chế độ — bắt đầu từ bản 0 đồng

|  | `tra_cuu` (mặc định) | `ai` |
|---|---|---|
| **Chi phí** | **0 đồng** | ~50.000–70.000đ/tháng |
| **Cần gì** | không cần gì | tài khoản Anthropic + thẻ quốc tế |
| Trả lời câu hỏi thường gặp | ✅ | ✅ |
| Khách hỏi theo cách khác lạ | ⚠️ cần khai `tu_khoa` | ✅ |
| Hiểu ngữ cảnh nhiều lượt | ❌ | ✅ |
| Dùng công cụ, làm theo quy trình | ❌ | ✅ |
| Biết im lặng khi không chắc | ✅ | ✅ |

Chế độ `tra_cuu` tìm câu trả lời bằng cách khớp từ khoá trong kho tri thức của
bạn. Nó không thông minh, nhưng nó **không bao giờ bịa** — không biết thì chuyển
người thật.

Với khoảng 80% câu hỏi CSKH lặp đi lặp lại, thế là đủ dùng.

> **Một điều phải biết về chế độ `tra_cuu`:** nó **không đọc `persona.md`**. Mọi
> luật kiểu *"khách hỏi X thì phải chuyển người thật"* bạn viết trong persona chỉ
> có hiệu lực ở chế độ `ai`. Ở chế độ miễn phí, thứ duy nhất bot đọc là **trang
> wiki** — nên ràng buộc nào quan trọng thì viết thẳng vào thân trang.
>
> Ví dụ thật: quán cà phê khai *"khách hỏi hôm nay còn chỗ không thì chuyển người"*.
> Bot vẫn trả về trang "Chỗ ngồi" (quán có 40 chỗ) — đúng về tra cứu, sai về
> nghiệp vụ. Cách sửa: thêm một dòng vào chính trang đó — *"Còn chỗ hay không thì
> anh/chị nhắn trực tiếp để bên em xem giúp ạ."*

**Đổi chế độ là đổi một dòng trong `.env`.** Cùng một kho tri thức, không phải
làm lại gì cả.

---

## Bốn thứ tạo nên con bot này

| | Ở đâu | Là gì |
|---|---|---|
| **Tính cách + luật** | `knowledge/persona.md` | Bot là ai, nói năng thế nào, tuyệt đối không được nói gì |
| **Kiến thức** | `knowledge/wiki/` | Bot biết gì — bảng giá, chính sách, quy trình |
| **Công cụ** | `agent_cskh/tools/` | Bot làm được gì — lưu khách, chuyển người thật, đọc ảnh |
| **Kỹ năng** | `skills/` | Bot làm theo quy trình nào — báo giá, xử lý phàn nàn |

Thứ bạn sửa thường xuyên nhất là **`knowledge/`**, và nó là Markdown thuần — sửa
được bằng Notepad, hoặc sửa thẳng từ điện thoại bằng lệnh `/themtrang` ngay trong
Zalo.

Kho tri thức theo phương pháp **LLM Wiki của Karpathy**: không vector database,
không embedding — chỉ Markdown liên kết nhau. Đó cũng chính là lý do bản 0 đồng
chạy được.

---

## Bot tự nói cho bạn biết nó còn thiếu gì

Mỗi lần bot không trả lời được, nó **ghi lại nguyên văn câu hỏi**. Báo cáo 20h
hàng ngày gom chúng lại:

> 📚 6 câu bot KHÔNG trả lời được — kho tri thức thiếu:
>    • "bên mình có ship đi Đà Nẵng không" (3 người hỏi)
>    • "bảo hành có tính rơi vỡ không"

Bạn viết thêm một trang, hôm sau bot trả lời được. Đây là vòng lặp học của cả hệ
thống — và nó chạy ở cả hai chế độ.

---

## Lệnh

```bash
uv run agent-cskh chat     # chat thử trong terminal
uv run agent-cskh check    # kiểm tra còn thiếu gì
uv run agent-cskh chay     # chạy thật trên Zalo
```

Chạy có tự khởi động lại: `.\run.ps1` (Windows) · `./run.sh` (macOS)

Lệnh trong Zalo: `/help` · `/whoami` · `/baocao` · `/themtrang` · `/nap` · `/nhan`

---

## Cài đặt

| | Windows | macOS |
|---|---|---|
| Cài `uv` | `winget install astral-sh.uv` | `brew install uv` |
| Cài thư viện | `uv sync` | `uv sync` |

`uv` tự lo Python, không cần cài Python riêng. Chi tiết:
[docs/00-cai-dat.md](docs/00-cai-dat.md)

> **macOS:** code viết đúng chuẩn đa nền tảng nhưng **chưa được chạy thử thật
> trên máy Mac**. Gặp lỗi thì mở issue giúp — đừng đoán là do mình làm sai.

---

## Cần biết trước khi đưa lên Zalo

- Gói Basic: **3.000 tin/tháng, 50 người dùng** — chi tiết ở
  [docs/02-gioi-han-zalo.md](docs/02-gioi-han-zalo.md)
- **Tắt máy là mất tin.** Zalo không lưu tin nhắn gửi lúc bot offline. Chạy thật
  lâu dài cần VPS.
- Zalo **không gửi/nhận được file tài liệu**. Khách gửi PDF thì bot không đọc được.
- Không có nút bấm. Tin nhắn tối đa 2.000 ký tự.

---

## Bảo mật

- **Không bao giờ commit file `.env`** — nó chứa token và API key. File này đã
  nằm sẵn trong `.gitignore`.
- `knowledge/` được git theo dõi (để có đường lùi khi sửa nhầm từ điện thoại).
  Nếu bạn đẩy lên GitHub thì **phải để repo private** — `wiki/internal/` chứa
  thông tin nội bộ như giá vốn.

Bot có ba lớp chặn không tắt được: không trả lời khi chưa tra kho, không tự xác
nhận đã nhận tiền, và không cho khách đọc tài liệu nội bộ. Đừng gỡ chúng.

---

## Chưa làm

- **Nhắn tin chủ động cho khách** (nhắc lịch, follow-up). Zalo có "cửa sổ gửi chủ
  động" nhưng chưa ai đo được nó, và mỗi tin chủ động ăn vào hạn mức 3.000
  tin/tháng của bạn. Bật mặc định một thứ chưa kiểm chứng trên OA thật của người
  khác là sai.
- **Facebook Fanpage, Telegram.** Lớp kênh (`agent_cskh/transport/`) đã tách sẵn
  để thêm, nhưng chưa có adapter.
- Notion, Google Sheets, Gmail — cần OAuth, mỗi người phải tự cấp.
- Tìm kiếm web.

---

## Kiểm thử

```bash
uv run pytest -q
uv run ruff check .
```

Nhóm test quan trọng nhất là `tests/test_authz.py` và `tests/test_wiki.py` —
chúng chặn tài liệu nội bộ rò ra cho khách. **Một test ở đó đỏ thì dừng lại sửa
trước khi làm gì khác.**
