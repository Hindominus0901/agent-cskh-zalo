---
name: tra-don-tao-don
description: Tra trạng thái đơn cho khách, và ghi nhận đơn mới để người thật xác nhận.
when: Khách hỏi "đơn của em tới đâu rồi", "khi nào nhận được hàng", hoặc nói muốn đặt hàng.
tools: [tra_don_hang, ghi_don_tam, kiem_ton_kho, chuyen_nguoi_that, luu_lead]
trang_thai: da_duyet
---

# Tra đơn và ghi đơn

Nguyên tắc gốc: **tra đơn thì nói đúng dữ liệu; đặt đơn thì luôn để người thật chốt.**

> **Ba công cụ trong kỹ năng này chỉ tồn tại khi shop đã nối dữ liệu đơn hàng**
> (`data/don_hang.csv`). Chưa nối thì chúng không xuất hiện — lúc đó gặp câu hỏi
> về đơn, dùng `chuyen_nguoi_that`. Đừng hứa tra giúp rồi mới phát hiện không tra được.

## Khách hỏi đơn tới đâu

**1. Xin mã đơn hoặc số điện thoại.** Chỉ cần một trong hai.

**2. Gọi `tra_don_hang`.**

**3. Đọc lại đúng những gì công cụ trả về.** Không thêm, không suy ra.

Công cụ nói *"Đang giao"* thì nói *"đang giao"*. **Đừng đoán** ngày nhận nếu dữ
liệu không có ngày — khách nhớ con số bạn nói, và họ sẽ đợi đúng ngày đó.

**4. Không tìm thấy đơn:**

- Hỏi lại xem mã đơn hoặc số điện thoại đã đúng chưa (khách hay đọc nhầm một số)
- Vẫn không ra → `chuyen_nguoi_that`
- **Tuyệt đối không đoán** trạng thái, và không nói "chắc đơn đang trên đường"

**5. Một số điện thoại ra nhiều đơn** thì hỏi mã đơn cụ thể, đừng đọc hết ra.

## Khách muốn đặt hàng

**1. Hỏi đủ ba thứ, từng câu một:** mặt hàng, số lượng, và yêu cầu thêm (màu,
size, giờ nhận).

**2. Còn hàng không thì đừng tự khẳng định.** Gọi `kiem_ton_kho`; nó chưa nối
được dữ liệu tồn thì nói thật là cần kiểm tra lại.

**3. Gọi `ghi_don_tam`.**

**4. Nói đúng bản chất việc vừa làm:**

> *"Dạ em ghi nhận rồi, bên em sẽ liên hệ lại để xác nhận đơn với anh/chị ạ."*

**KHÔNG nói "đã đặt hàng thành công".** Chưa ai xác nhận cả. Bot đọc sai một chữ
trong địa chỉ hoặc số lượng thì thành một đơn sai được giao đi thật — và người
chịu là khách.

**5. Không xác nhận giá cuối, không hứa ngày giao, không xác nhận đã nhận tiền.**

## Xong khi

- Mọi thông tin về đơn đều trích từ `tra_don_hang`, không có chữ nào tự suy
- Đặt đơn thì đã gọi `ghi_don_tam` và đã chuyển người thật
- Khách hiểu rõ là **đang chờ xác nhận**, không phải đã xong

## Bẫy hay gặp

- **Đoán ngày nhận hàng.** *"Chắc mai là tới ạ"* — khách sẽ đợi đúng ngày mai.
- **Nói "đã đặt hàng thành công".** Chưa ai xác nhận.
- **Tự khẳng định còn hàng.** Hết hàng mà nhận đơn là hỏng việc thật.
- **Đọc hết mười đơn ra khi khách chỉ hỏi một.**
- **Hứa tra đơn khi shop chưa nối dữ liệu.** Kiểm bằng cách xem công cụ có tồn
  tại không, đừng đoán.
