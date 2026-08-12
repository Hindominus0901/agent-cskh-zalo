---
name: _MAU
description: KHUÔN MẪU — chép thư mục này rồi sửa. Bản thân nó đang tắt.
when: Không bao giờ. Trường trang_thai đang là "tat".
tools: [doc_trang, tim_trang]
trang_thai: tat
---

# Tên kỹ năng

> **Đây là khuôn mẫu.** `trang_thai: tat` nên bot không bao giờ thấy nó.
>
> Viết kỹ năng mới: chép cả thư mục `_MAU/` thành `ten-ky-nang-cua-ban/`, sửa
> frontmatter, đổi `trang_thai` thành `da_duyet`.
>
> **Tên kỹ năng chính là TÊN THƯ MỤC**, không phải trường `name`.

Nguyên tắc gốc: **một câu in đậm nói cái quan trọng nhất của cả kỹ năng này.**

Câu này là thứ bot đọc kỹ nhất. Viết nó như một lời khuyên bạn muốn nhân viên mới
nhớ mãi, không phải như một tiêu đề.

## Các bước

**1. Bước đầu tiên, viết ở thể mệnh lệnh.**

Giải thích ngắn *vì sao* bước này quan trọng. Bot làm theo tốt hơn hẳn khi biết lý
do — và người sau đọc lại cũng không xoá nhầm.

**2. Bước tiếp theo.**

Chỗ nào có ranh giới thì nói thẳng: *"Không có trong kho thì đừng suy ra."*

**3. Bước cuối cùng thường là dừng lại hoặc bàn giao.**

## Xong khi

Danh sách kiểm — mỗi dòng phải **kiểm được**, không phải một mong muốn.

- Điều kiện cụ thể 1
- Điều kiện cụ thể 2

## Bẫy hay gặp

Phần đáng giá nhất của cả file, và cũng là phần hay bị viết qua loa nhất.

Viết **lỗi thật đã xảy ra**, không phải lời khuyên chung chung.

- **Tên cái bẫy in đậm.** Rồi giải thích vì sao nó hấp dẫn, và vì sao nó sai.
- **Một cái bẫy khác.** "Hãy cẩn thận" không phải một cái bẫy — "tự nới giá khi
  thấy khách sắp bỏ đi" mới là.

---

## Ghi chú về frontmatter

| Trường | Việc |
|---|---|
| `description` | Một dòng, hiện trong mục lục prompt. Bot dựa vào đây để biết kỹ năng này làm gì. |
| `when` | **Quan trọng ngang description.** Nói rõ KHI NÀO dùng. Thiếu nó thì kỹ năng nằm im không ai gọi. |
| `tools` | Các công cụ kỹ năng này cần. Hiện ra trong mục lục để bot biết trước nó cần gì. |
| `trang_thai` | `da_duyet` (dùng được) · `nhap` (chờ duyệt) · `tat` (bỏ qua) |

Viết xong thì kiểm bằng:

```bash
uv run agent-cskh check
```
