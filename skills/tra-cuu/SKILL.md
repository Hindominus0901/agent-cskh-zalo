---
name: tra-cuu
description: Trả lời một câu hỏi dựa trên kho tri thức, dẫn nguồn, và nói thẳng khi kho không có.
when: Khách hỏi bất cứ điều gì mà câu trả lời có thể nằm trong kho — sản phẩm, giá, chính sách, quy trình.
tools: [doc_trang, tim_trang, tim_hoi_thoai]
trang_thai: da_duyet
---

# Tra cứu

Nguyên tắc gốc: **trả lời từ cái đã đọc, không từ cái mình tưởng là biết.**

## Các bước

**1. Đọc danh mục kho tri thức** (đã có sẵn trong hướng dẫn hệ thống) và chọn
những trang có khả năng liên quan.

**2. Đọc toàn văn những trang đó** bằng `doc_trang`.

Không trả lời chỉ dựa vào dòng tóm tắt trong danh mục — summary là để **chọn**
trang, không phải để **trả lời**. Nó bị cắt ngắn có chủ đích, và thứ bị cắt đi
thường chính là điều kiện và ngoại lệ.

**3. Danh mục không có gì khớp** thì thử `tim_trang` với từ khoá khác — tìm được
cả khi không dấu. Khách nhắc tới chuyện đã bàn trước đây thì thử `tim_hoi_thoai`.

**4. Trả lời.**

- Kết luận trước, chi tiết sau
- Bám sát chữ trong trang. Đừng diễn giải rộng ra.
- Chỗ nào là suy luận của mình chứ không có trong kho thì **nói rõ là suy luận**

**5. Kho không có thì nói thẳng.**

*"Dạ phần này em chưa nắm chắc nên chưa dám trả lời anh/chị ạ."* Rồi chuyển người
thật. **Không suy đoán, không lấp bằng kiến thức chung.**

Câu này quan trọng hơn nó tưởng: kiến thức chung nghe rất hợp lý, và đúng ở phần
lớn trường hợp — nhưng thứ làm hỏng việc luôn là số liệu riêng của doanh nghiệp
này: giá của họ, chính sách của họ, thứ họ đã hứa với khách nào.

## Xong khi

- Câu trả lời trỏ được vào một trang cụ thể, hoặc nói rõ là kho chưa có
- Không có câu nào không kiểm được nguồn

## Bẫy hay gặp

- **Trả lời từ summary.** Summary bị cắt ngắn có chủ đích, thiếu điều kiện và
  ngoại lệ.
- **Trộn kiến thức chung vào mà không đánh dấu.** Khách không phân biệt được đâu
  là chính sách thật của shop, đâu là bot đoán.
- **Tìm một lần không ra rồi kết luận "kho không có".** Thử ít nhất hai bộ từ
  khoá khác nhau trước khi kết luận.
- **Đọc trang rồi trả lời rộng hơn trang.** Trang nói bảo hành 24 tháng; khách
  hỏi có bảo hành rơi vỡ không; trang không nói. Đó là "kho chưa có", không phải
  "chắc là có".
