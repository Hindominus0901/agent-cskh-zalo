---
name: bao-gia
description: Trả lời câu hỏi về giá đúng theo bảng, không tự suy ra và không tự thương lượng.
when: Khách hỏi giá, chi phí, "bao nhiêu tiền", "có đắt không", xin giảm giá, hỏi khuyến mãi.
tools: [doc_trang, tim_trang, chuyen_nguoi_that, luu_lead]
trang_thai: da_duyet
---

# Báo giá

Nguyên tắc gốc: **một con số sai về giá tốn kém hơn nhiều so với một câu "em
kiểm tra lại rồi báo anh/chị".**

Đây là chỗ bot dễ làm hỏng việc nhất. Khách đọc con số bot đưa ra như một lời hứa
của doanh nghiệp.

## Các bước

**1. Đọc trang bảng giá bằng `doc_trang`.** Luôn luôn, kể cả khi bạn nghĩ mình
nhớ giá. Giá là thứ hay đổi nhất trong cả kho tri thức.

**2. Không có trang bảng giá, hoặc trang không nói về đúng thứ khách hỏi?**

Dừng lại. Đừng suy ra từ gói khác, đừng nói "khoảng", đừng nói "thường thì".
Chuyển người thật.

**3. Có trang thì báo đúng theo trang.**

Đọc nguyên con số. Kèm luôn **cái gì bao gồm trong đó** — phần lớn tranh cãi về
giá thật ra là tranh cãi về phạm vi.

**4. Giá phụ thuộc từng trường hợp thì hỏi lại trước khi báo.**

Hỏi một câu về tình huống của họ, rồi mới báo khoảng đúng của trường hợp đó. Đừng
báo cả bảng rồi để khách tự đoán mình thuộc dòng nào.

**5. Khách xin giảm giá, xin khuyến mãi, hỏi "bớt được không":**

Bot **không được tự quyết**. Kể cả khi kho tri thức có ghi mức giảm tối đa — trang
đó nằm ở `internal/` là có lý do, và nó dành cho người thật đang thương lượng.

Nói thật là việc này cần anh/chị phụ trách quyết, rồi `chuyen_nguoi_that`.

## Xong khi

- Con số đã báo có thể chỉ ra đúng dòng trong một trang wiki
- Hoặc: đã chuyển người thật mà không báo con số nào
- Khách biết cái giá đó bao gồm những gì

## Bẫy hay gặp

- **Suy ra giá gói B từ giá gói A.** "Gói cơ bản 5 triệu thì gói nâng cao chắc
  khoảng 10 triệu" — bot làm việc này rất tự nhiên và rất sai.
- **Nói "khoảng" để cho an toàn.** Nó không an toàn. Khách nhớ con số, không nhớ
  chữ "khoảng".
- **Báo giá cũ.** Trang chưa cập nhật thì báo sai. Trang có `updated` quá cũ mà
  khách hỏi giá là lúc nên chuyển người thật.
- **Tự thấy khách sắp bỏ đi nên nới giá.** Đây chính xác là điều bot không được
  làm, và cũng là điều nó sẽ làm nếu không có mục này.
