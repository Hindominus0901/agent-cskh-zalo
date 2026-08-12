# Ba trang wiki mẫu — chép theo là được

Kho tri thức của bạn đang trống, và đó là **cố ý**: nội dung phải là của bạn, không
phải của một shop tưởng tượng nào đó.

Nhưng nhìn một trang hoàn chỉnh vẫn dễ hơn đọc luật. Ba trang dưới đây là của một
shop quần áo giả định — chép cấu trúc, thay nội dung bằng của bạn.

> Luật đầy đủ ở [`knowledge/CLAUDE.md`](../knowledge/CLAUDE.md). Trang này chỉ là
> ví dụ.

---

## Trang 1 — công khai, ai cũng đọc được

Lưu thành `knowledge/wiki/public/bang-gia.md`

```markdown
---
title: Bảng giá
summary: Giá áo, quần, phụ kiện và mức giảm khi mua từ 2 món.
tu_khoa: ["bao nhieu tien", "gia", "gia ca", "mac khong", "co dat khong", "bang gia", "tam bao nhieu"]
tags: [bang-gia]
updated: 2026-08-12
---

# Bảng giá

- Áo thun cotton: 250.000đ
- Quần jean: 450.000đ
- Mũ, túi vải: 120.000đ

Mua từ 2 món giảm 10%. Giá đã gồm thuế, chưa gồm phí giao hàng.

Liên quan: [[giao-hang]], [[doi-tra]]
```

**Chỗ đáng để ý nhất là `tu_khoa`.** Bảy cách nói, và chỉ hai trong số đó có chữ
"giá". Khách thật gõ *"cái này mắc không"*, *"tầm bao nhiêu"* — không ai gõ *"cho
tôi xem bảng giá"*.

Cách lấy: **mở lại tin nhắn khách cũ và chép nguyên văn.** Đừng ngồi nghĩ ra.

---

## Trang 2 — khách quen, người lạ không thấy

Lưu thành `knowledge/wiki/hocvien/uu-dai-khach-cu.md`

```markdown
---
title: Ưu đãi khách cũ
summary: Mức giảm dành riêng cho khách đã mua, và cách dùng.
tu_khoa: ["uu dai", "khach cu co gi", "mua lan hai", "giam them"]
updated: 2026-08-12
---

# Ưu đãi khách cũ

Khách đã mua từ lần thứ hai được giảm thêm 5%, cộng dồn với khuyến mãi đang chạy.

Không cần mã, chỉ cần nhắn cho bên em là bên em tự áp.

Liên quan: [[bang-gia]]
```

Đây **không phải bí mật** — chỉ là thứ nói với người chưa mua thì vừa thừa vừa dễ
gây hiểu nhầm ("sao tôi không được giảm?").

---

## Trang 3 — nội bộ, khách không bao giờ thấy

Lưu thành `knowledge/wiki/internal/muc-giam-toi-da.md`

```markdown
---
title: Mức giảm tối đa được phép
summary: Nhân viên được giảm tới đâu mà không cần hỏi, và khi nào phải hỏi.
tu_khoa: ["giam toi da", "bot duoc bao nhieu", "duoc giam may phan tram"]
updated: 2026-08-12
---

# Mức giảm tối đa được phép

Nhân viên tự quyết được tới 15%. Trên mức đó phải hỏi quản lý.

Đơn trên 3 triệu: miễn phí giao hàng, không cần hỏi.

Khách mặc cả gắt thì giữ giá và tặng thêm phụ kiện — đừng phá giá niêm yết.
```

Trang này đặt nhầm vào `public/` là **khách sẽ biết bạn còn giảm được bao nhiêu**,
và mọi cuộc mặc cả từ đó về sau đều bắt đầu từ con số 15%.

Bot vẫn đọc được trang này khi nói chuyện với **nhân viên**, nên nó vẫn hữu ích —
chỉ là không rò ra ngoài.

---

## Sau khi viết xong

```bash
uv run python scripts/wiki_index.py
```

Nó dựng lại danh mục và **soát lỗi**: thiếu `summary`, thiếu `tu_khoa`, trang dài
quá 1400 ký tự, liên kết `[[...]]` gãy, trùng tên file, tên file có dấu.

Bot đang chạy thì nhắn **"nạp lại kho"** — nạp ngay, không cần khởi động lại.

Rồi thử bằng chính câu khách hay hỏi:

```bash
uv run agent-cskh chat
```

Bot trả về sai trang thì **thêm cách hỏi đó vào `tu_khoa` của trang đúng** — đó là
cách sửa nhanh nhất và đúng nhất.
