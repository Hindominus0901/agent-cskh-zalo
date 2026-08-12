# Bốn trụ cột — bot sai thì sửa ở đâu

Đọc file này **một lần** khi mới nhận bot. Nó trả lời đúng một câu hỏi, và là câu
bạn sẽ hỏi nhiều nhất:

> *Bot vừa trả lời sai. Giờ tôi mở file nào?*

---

## Bốn trụ cột, một câu mỗi cái

| Trụ | Ở đâu | Trả lời câu |
|---|---|---|
| **Tính cách** | `knowledge/persona.md` | Bot **là ai**, nói năng thế nào, tuyệt đối không được nói gì |
| **Kiến thức** | `knowledge/wiki/` | Bot **biết** gì |
| **Kỹ năng** | `skills/` | Bot **làm thế nào** |
| **Công cụ** | `agent_cskh/tools/` | Bot **làm được** gì |

Hai trụ giữa hay bị lẫn nhất, nên nói thẳng:

> `knowledge/wiki/` = bot **biết** gì · `skills/` = bot **làm thế nào**
>
> *"Bảo hành 24 tháng"* là **kiến thức**.
> *"Nghe phàn nàn thì ghi nhận trước, đừng thanh minh"* là **kỹ năng**.

Bạn sửa `knowledge/` gần như mỗi tuần. Sửa `persona.md` vài lần rồi thôi. Sửa
`skills/` khi thấy bot làm đúng việc nhưng sai cách. Hiếm khi đụng `tools/`.

---

## Bảng chẩn đoán

Bot vừa làm sai. Tìm dòng gần nhất với triệu chứng:

| Bot làm gì | Sửa trụ nào | Sửa cụ thể |
|---|---|---|
| Nói *"em chưa nắm chắc"* cho câu **đã có** trong kho | Kiến thức | Thêm cách khách vừa hỏi vào `tu_khoa` của trang đúng |
| Trả về **sai trang** | Kiến thức | Bỏ từ khoá trùng ở trang sai, thêm từ đặc trưng cho trang đúng |
| Trả lời **đúng nhưng thiếu** phần sau | Kiến thức | Trang dài quá 1400 ký tự — tách trang |
| **Bịa** một con số | Kiến thức | Kho chưa có trang đó. Viết trang. |
| Xưng hô sai, giọng cứng, dài dòng | Tính cách | `persona.md` — mục *Cách nói* |
| Nói câu sáo rỗng kiểu máy | Tính cách | `persona.md` — mục *Tuyệt đối không viết* |
| Tự báo giá / hứa giao hàng / xác nhận đã nhận tiền | Tính cách | `persona.md` — mục *Ranh giới*. **Kiểm ngay, đây là lỗi nặng** |
| Trả lời đúng nhưng **sai thứ tự** (báo giá trước khi hỏi nhu cầu) | Kỹ năng | Sửa skill tương ứng trong `skills/` |
| Không biết xử lý một loại tình huống | Kỹ năng | Viết skill mới — chép `skills/_MAU/` |
| Hứa tra đơn rồi không tra được | Công cụ | Chưa nối `data/don_hang.csv` |
| Cần làm một việc hệ thống chưa có | Công cụ | Việc của lập trình viên. Đừng hứa với khách. |

**Chưa rõ trụ nào?** Chín trên mười lần là **kiến thức**. Bắt đầu từ đó.

---

## Cách sửa nhanh nhất, theo thứ tự

**1. Tái hiện lại trong máy**

```bash
uv run agent-cskh chat
```

Gõ đúng câu khách vừa hỏi. Rẻ hơn nhiều so với thử trên Zalo thật.

**2. Sửa file** theo bảng trên.

**3. Kiểm**

```bash
uv run python scripts/wiki_index.py
uv run agent-cskh check
```

**4. Nạp lại** — nhắn **"nạp lại kho"** cho bot. Không cần khởi động lại.

> Sửa `persona.md` hoặc `.env` thì **phải khởi động lại** — hai file đó chỉ đọc
> lúc bot khởi động. Sửa `knowledge/wiki/` và `skills/` thì chỉ cần nạp lại.

---

## Trụ nào chạy ở chế độ nào

Đây là chỗ hay gây bất ngờ nhất, nên để riêng một bảng:

| Trụ cột | `tra_cuu` (0 đồng) | `ai` |
|---|:---:|:---:|
| Kiến thức (`knowledge/wiki/`) | ✅ | ✅ |
| Tính cách (`persona.md`) | ❌ | ✅ |
| Kỹ năng (`skills/`) | ❌ | ✅ |
| Công cụ (`tools/`) | ❌ | ✅ |

**Ở bản 0 đồng, chỉ một trụ hoạt động.** Bot tra kho tri thức rồi trả về nội dung
trang khớp nhất — không đọc persona, không dùng kỹ năng, không gọi công cụ.

Hệ quả cụ thể phải biết:

- Luật *"khách hỏi X thì phải chuyển người thật"* bạn viết trong `persona.md`
  **không có hiệu lực**. Ràng buộc nào quan trọng thì viết thẳng vào **thân trang wiki**.
- Bot **không lưu được** số điện thoại khách (`luu_lead` là công cụ).
- Bot **không xem được ảnh** — khách gửi ảnh chuyển khoản thì bot nói thật và
  chuyển người.
- Bot vẫn **không bao giờ bịa**, và vẫn ghi lại câu nó không trả lời được.

Đổi sang `ai` là đổi một dòng trong `.env`. Cùng một kho tri thức.

---

## Vòng lặp học — thứ làm bot khá lên

Mỗi lần bot không trả lời được, nó **ghi lại nguyên văn câu hỏi**. Báo cáo 20h
hàng ngày gom lại:

> 📚 6 câu bot KHÔNG trả lời được:
>    • "bên mình có ship đi Đà Nẵng không" (3 người hỏi)

Đây là **danh sách việc cần làm, đã sắp theo số người hỏi**. Viết thêm một trang,
hôm sau bot trả lời được.

Chạy ở **cả hai chế độ**. Xem bất cứ lúc nào bằng cách nhắn *"báo cáo hôm nay"*.

Nếu bạn chỉ làm một việc mỗi tuần với con bot này, hãy làm việc đó.

---

## Ba lớp chặn không được gỡ

Bot có ba thứ không tắt được, và chúng là lý do bạn dám để nó nói chuyện với
khách thật:

1. **Không trả lời khi chưa tra kho** — trả lời dài mà chưa đọc trang nào thì bị
   thay bằng câu thoái lui, và câu hỏi được ghi lại
2. **Không tự xác nhận đã nhận tiền** — kể cả khi khách gửi ảnh chuyển khoản
3. **Không cho khách đọc tài liệu nội bộ** — quyền đến từ **thư mục**, không từ
   nội dung file

Ai đó sửa code làm hỏng một trong ba, `uv run pytest -q` sẽ đỏ ngay.

---

## Đọc tiếp

- [`knowledge/CLAUDE.md`](../knowledge/CLAUDE.md) — luật viết kho tri thức
- [`docs/vi-du-trang-wiki.md`](vi-du-trang-wiki.md) — ba trang mẫu để chép theo
- [`skills/_MAU/SKILL.md`](../skills/_MAU/SKILL.md) — khuôn viết kỹ năng mới
- [`docs/02-gioi-han-zalo.md`](02-gioi-han-zalo.md) — Zalo không làm được gì
