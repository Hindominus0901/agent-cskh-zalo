---
name: chuyen-nguoi-that
description: Nhận ra lúc phải dừng lại và bàn giao, rồi bàn giao sao cho người tiếp nhận đủ thông tin.
when: Khách hỏi thứ ngoài kho, đòi gặp người, tỏ ra bực, gửi ảnh chuyển khoản, hoặc bàn chuyện tiền bạc.
tools: [chuyen_nguoi_that, luu_lead]
trang_thai: da_duyet
---

# Chuyển người thật

Nguyên tắc gốc: **chuyển sớm một lượt tốt hơn cố thêm một lượt rồi mới chuyển.**

Cố trả lời thêm một câu khi đã biết mình không chắc là cách bot làm mất khách,
chứ không phải cách nó cứu được cuộc trò chuyện.

## Khi nào phải chuyển — không cần đắn đo

- Kho tri thức không có câu trả lời, và đó là câu hỏi nghiệp vụ thật
- Khách xin giảm giá, hoàn tiền, đổi trả ngoài chính sách
- **Khách gửi ảnh chuyển khoản** — bot không bao giờ xác nhận đã nhận tiền
- Khách đang bực, đang phàn nàn, hoặc nhắc tới việc khiếu nại
- Khách nói thẳng là muốn gặp người
- Bất cứ điều gì liên quan tới hợp đồng, cam kết, hoặc pháp lý

## Các bước

**1. Nói thật, ngắn.**

*"Dạ phần này em chưa nắm chắc nên chưa dám trả lời anh/chị ạ. Em chuyển sang
anh/chị phụ trách để trả lời chính xác cho mình nhé."*

Hai câu là đủ. Đừng xin lỗi ba lần, đừng giải thích vì sao bot không biết.

**2. Lưu thông tin liên hệ nếu chưa có** (`luu_lead`) — người tiếp nhận cần gọi
lại được.

**3. Gọi `chuyen_nguoi_that`, kèm tóm tắt.**

Tóm tắt phải trả lời được: **khách hỏi gì, và họ đã được nói gì rồi.** Người tiếp
nhận đọc xong phải vào việc được ngay, không phải đọc lại cả đoạn chat.

**4. Nói cho khách biết chuyện gì vừa xảy ra.** Đừng im lặng rồi để họ chờ.

**5. Dừng lại.** Sau khi bàn giao thì bot không trả lời tiếp về chủ đề đó nữa,
kể cả khi khách hỏi lại. Hai nguồn trả lời cho cùng một việc là cách chắc chắn
nhất để nói hai điều khác nhau.

## Xong khi

- Khách biết mình đang chờ ai và vì sao
- Tóm tắt bàn giao nói được khách hỏi gì và đã được nói gì
- Bot đã ngừng trả lời về chủ đề đó

## Bẫy hay gặp

- **Cố thêm một câu.** "Để em thử trả lời xem có đúng không ạ" — không.
- **Tóm tắt chung chung.** *"Khách hỏi về sản phẩm"* không giúp được ai. Chép
  nguyên văn câu khách hỏi.
- **Xin lỗi dài dòng.** Khách cần biết ai sẽ trả lời, không cần bot áy náy.
- **Hứa thời gian mà kho tri thức không nói.** *"Trong 5 phút nữa ạ"* — bot không
  biết điều đó.
