# Schema kho tri thức — LLM Wiki

File này là luật viết kho tri thức. Đọc trước khi thêm trang đầu tiên.

> **Dành cho MỌI coding agent, không riêng Claude.** Tên file là `CLAUDE.md` chỉ
> vì Claude Code tự nạp file này khi làm việc trong thư mục `knowledge/` — tiện
> thì giữ. Codex và Cursor đọc nó theo đường dẫn, và cũng **bắt buộc** phải đọc
> trước khi viết trang đầu tiên.

Theo phương pháp **LLM Wiki của Andrej Karpathy**: không vector database, không
embedding — chỉ Markdown liên kết với nhau, người đọc được, người sửa được.

Nguồn gốc: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

Đây cũng chính là lý do bot chạy được ở **chế độ `tra_cuu` — 0 đồng, không cần
API key**. Tìm kiếm là regex bỏ dấu trên Markdown, không phải gọi model.

---

## Cấu trúc

```
knowledge/
├─ CLAUDE.md          ← file này. Luật chơi.
├─ index.md           ← bản đồ tổng. Nằm trong system prompt của bot.
├─ persona.md         ← bot là ai, nói năng thế nào
├─ raw/               ← nguồn gốc. CHỈ ĐỌC, không bao giờ sửa.
│  ├─ public/
│  └─ internal/
└─ wiki/              ← trang bot đọc
   ├─ public/         ← ai cũng đọc được, kể cả khách lạ
   ├─ hocvien/        ← khách quen / thành viên + nhân viên + chủ
   └─ internal/       ← chỉ nhân viên và chủ
```

**Quy tắc phân quyền tuyệt đối: thư mục quyết định ai đọc được.**

| Thư mục | Khách lạ | Khách quen | Nhân viên / chủ |
|---|:---:|:---:|:---:|
| `wiki/public/` | ✅ | ✅ | ✅ |
| `wiki/hocvien/` | ❌ | ✅ | ✅ |
| `wiki/internal/` | ❌ | ❌ | ✅ |

Không có ngoại lệ, không có cờ đánh dấu trong nội dung. Người không được phép
**không thấy cả tên trang** trong danh mục.

**Phân vân thì đặt vào `internal/`.** Mặc định phải là an toàn. Nâng quyền cho
một trang là việc làm sau, có chủ đích; hạ quyền sau khi đã lộ thì không làm được.

Những thứ gần như luôn phải ở `internal/`: giá vốn, biên lợi nhuận, hoa hồng,
kịch bản xử lý khách khó tính, ghi chú về đối thủ, mức giảm giá tối đa được phép.

---

## Định dạng một trang

Mỗi file trong `wiki/` bắt buộc có frontmatter:

```markdown
---
title: Bảng giá 2026
summary: Ba gói dịch vụ, giá từng gói và những gì bao gồm.
tu_khoa: ["bao nhieu tien", "gia", "chi phi", "mac khong", "co dat khong"]
tags: [bang-gia, dich-vu]
sources: [raw/public/bang-gia-2026.pdf]
updated: 2026-08-08
---

# Bảng giá 2026

Nội dung...

Liên quan: [[cac-goi-dich-vu]], [[chinh-sach-doi-tra]]
```

### `summary` — trường quan trọng nhất

Nó là **dòng duy nhất** đại diện cho trang này trong `index.md`, và index là thứ
bot nhìn thấy trước tiên. Một summary mơ hồ khiến bot không tìm ra trang, dù nội
dung bên trong đúng đến đâu.

Viết như đang mô tả cho người chưa đọc trang: *cái gì, cho ai, trả lời được câu
hỏi nào.*

### `tu_khoa` — thứ quyết định chế độ 0 đồng chạy được hay không

Đây là **cách khách hay hỏi, nguyên văn**. Khác hẳn `tags` (phân loại cho người
quản trị đọc).

Tìm kiếm ở chế độ `tra_cuu` là regex bỏ dấu. Nó khớp "giá" nhưng trượt sạch
"mắc không", "bao nhiêu xu", "có đắt không", "tầm bao nhiêu" — trong khi đó mới
là cách khách thật gõ. Ba dòng `tu_khoa` bù đúng chỗ hổng đó.

Viết **không dấu cũng được** — hệ thống tự bỏ dấu khi so khớp.

Cách lấy: mở lại tin nhắn khách cũ, chép nguyên văn cách họ hỏi. Đừng ngồi nghĩ
ra.

### Còn lại

- Liên kết chéo dùng cú pháp Obsidian `[[ten-file]]` (không cần đuôi `.md`).
- Tên file: chữ thường, không dấu, nối bằng gạch ngang. `bang-gia-2026.md`.

---

## Độ dài: viết ngắn, tách nhiều trang

Bot cắt ở **1400 ký tự** khi trả lời (giới hạn tin nhắn Zalo là 2000). Một trang
3000 chữ tức là hơn nửa nội dung không bao giờ tới được khách.

**Mỗi trang trả lời đúng một câu hỏi.** "Bảng giá" và "chính sách đổi trả" là hai
trang, không phải hai mục trong một trang. Tách ra thì bot cũng chọn đúng hơn.

---

## Quy trình thêm một trang

1. Đặt file gốc (nếu có) vào `raw/public/` hoặc `raw/internal/` — **không sửa
   file gốc**.
2. Hỏi chủ doanh nghiệp những chỗ mơ hồ **trước khi viết**. Không đoán.
3. Viết trang trong `wiki/` cùng mức quyền với thư mục raw tương ứng.
4. **Cập nhật những trang liên quan đã có.** Một nguồn mới thường chạm tới nhiều
   trang — bảng giá mới thì trang gói dịch vụ, trang FAQ, trang quy trình đều
   phải sửa theo. Đây là bước hay bị bỏ sót nhất và cũng là bước tạo ra giá trị
   thật: kho tri thức bồi đắp lên nhau thay vì chỉ chất đống.

   Nếu thêm xong mà **không trang nào khác đổi**, dừng lại tự hỏi có thật thế không.
5. `uv run python scripts/wiki_index.py` — dựng lại `index.md`, soát liên kết gãy.
6. Bot đang chạy thì nhắn “nạp lại kho” để nạp lại, không cần khởi động lại.

---

## Quy trình trả lời (bot làm, ghi ở đây để người sửa kho hiểu)

1. Đọc `index.md` (đã có sẵn trong prompt).
2. Chọn trang có khả năng liên quan, **đọc toàn văn**.
3. Trả lời **chỉ dựa trên nội dung đã đọc**.
4. Kho không có thông tin: nói thẳng là chưa có, chuyển người phụ trách, và **ghi
   nguyên văn câu hỏi vào bảng `thieu_trang`**. **Không suy đoán, không lấp chỗ
   trống bằng kiến thức chung.**

Bước 4 là vòng lặp học của cả hệ thống. Báo cáo 20h hàng ngày gom những câu đó
lại: *"hôm nay 6 câu không trả lời được, 3 người hỏi về bảo hành"*. Chủ bot viết
thêm một trang, hôm sau bot trả lời được.

---

## Bảo trì

- Hai trang mâu thuẫn nhau thì **sửa ngay**, đừng để song song — bot sẽ chọn một
  trong hai và trả lời sai một nửa số lần.
- Thông tin hết hạn (giá cũ, khuyến mãi đã kết thúc) thì **xoá**, đừng chỉ ghi
  chú "đã cũ". Bot đọc cả phần ghi chú.
- Chạy `scripts/wiki_index.py` để soát: trang thiếu `summary`, thiếu `tu_khoa`,
  liên kết `[[...]]` gãy, index lệch với thư mục.
- Sửa được từ điện thoại, nói bằng lời: “thêm trang công khai <tên>”, “sửa trang <tên>”,
  “xoá trang <tên>”, “có những trang nào”. Việc xoá và sửa bot hỏi lại trước khi làm.
  Bản cũ luôn được giữ lại thành `.md.bak`.
- Phương pháp này chạy tốt tới khoảng **vài trăm trang**. Vượt mức đó thì cân
  nhắc tìm kiếm bằng embedding — nhưng chỉ khi đã thật sự vượt, không phải vì lo xa.
