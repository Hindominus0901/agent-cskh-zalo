---
name: soat-kho
description: Rà lại kho tri thức — trang thiếu summary, thiếu tu_khoa, quá dài, mâu thuẫn, liên kết gãy.
when: Chủ bot nhờ kiểm tra kho, hoặc sau khi vừa thêm một loạt trang mới.
tools: [doc_trang, tim_trang]
trang_thai: da_duyet
---

# Soát kho tri thức

Nguyên tắc gốc: **một trang bot không tìm ra thì coi như không tồn tại.**

Kho tri thức hỏng không bao giờ báo lỗi. Nó chỉ im lặng khiến bot trả lời "em
chưa nắm chắc" cho một câu mà câu trả lời đang nằm ngay trong kho.

## Các bước

**1. Chạy máy trước.**

```bash
uv run python scripts/wiki_index.py
```

Nó bắt được: thiếu `summary`, thiếu `tu_khoa`, trang dài quá 1400 ký tự, liên kết
`[[...]]` gãy. Sửa hết những cái này trước khi đọc bằng mắt.

**2. Soát `summary` bằng mắt.**

Đọc riêng dòng summary, không đọc thân bài. Tự hỏi: *nếu chỉ có dòng này, mình có
biết khi nào cần mở trang này không?*

*"Thông tin về sản phẩm"* — không biết. *"Ba gói dịch vụ, giá từng gói và những gì
bao gồm"* — biết.

**3. Soát `tu_khoa` — bước đáng giá nhất.**

Với mỗi trang, tự hỏi: khách gõ những chữ nào thì phải ra trang này? Rồi kiểm tra
xem những chữ đó có trong `tu_khoa` không.

Cách kiểm nhanh: `uv run agent-cskh chat`, gõ đúng cách khách hay hỏi, xem có ra
trang đó không.

Nhớ rằng ở chế độ `tra_cuu` thì tìm kiếm là regex — "giá" khớp, "mắc không" thì
không, trừ khi có trong `tu_khoa`.

**4. Tìm mâu thuẫn.**

Dùng `tim_trang` với những từ hay trùng: giá, bảo hành, đổi trả, giao hàng. Hai
trang cùng nói về một thứ mà nói khác nhau là lỗi nặng nhất — bot sẽ chọn một
trong hai và trả lời sai một nửa số lần.

Sửa ngay, đừng để song song.

**5. Tìm thông tin hết hạn.**

Giá cũ, khuyến mãi đã kết thúc, chính sách đã đổi. **Xoá**, đừng chỉ ghi chú "đã
cũ" — bot đọc cả phần ghi chú.

**6. Đọc báo cáo hàng ngày.**

Mục *"câu bot KHÔNG trả lời được"* là danh sách trang cần viết, đã được sắp theo
số người hỏi. Đó là nguồn tốt nhất để biết viết gì tiếp — tốt hơn mọi phỏng đoán.

## Xong khi

- `scripts/wiki_index.py` không báo vấn đề nào
- Mọi summary đọc riêng vẫn biết khi nào cần mở trang
- Mọi trang có `tu_khoa` lấy từ cách khách hỏi thật
- Không hai trang nào nói khác nhau về cùng một thứ

## Bẫy hay gặp

- **Chỉ chạy script rồi coi là xong.** Script bắt được lỗi hình thức, không bắt
  được mâu thuẫn nội dung hay summary vô nghĩa.
- **Viết `tu_khoa` bằng cách ngồi nghĩ.** Mở lại tin nhắn khách cũ mà chép.
- **Thêm trang mới mà không sửa trang cũ liên quan.** Bảng giá mới thì trang gói
  dịch vụ, trang FAQ, trang quy trình đều phải sửa theo.
- **Gộp nhiều chủ đề vào một trang cho gọn.** Bot cắt ở 1400 ký tự, và trang gộp
  cũng làm điểm tìm kiếm loãng đi.
