# Dùng bot trên Zalo — cho bạn và cho khách

Bot chạy rồi. Giờ là phần **không ai đọc tài liệu kỹ thuật nào nói cho biết**:
làm sao để khách tìm ra bot, và làm sao để họ nói chuyện với nó mà không bực.

---

## 1. Gửi bot cho một khách mới

Mở mini app **Zalo Bot Creator** → chọn bot → mục **Chia sẻ** → copy link.

Link có dạng:

```
https://bot.zaloplatforms.com/bots/1234567890123456789
```

Nó tự chuyển hướng sang `zalo.me/<id>`. Khách bấm vào là **mở thẳng cửa sổ chat
với bot**, không phải cài gì thêm.

Gửi link này ở đâu cũng được: tin nhắn, bài đăng, website, mã QR in ra dán ở quán.

> **Nhớ hạn mức:** gói Basic chỉ **50 người dùng**. Người thứ 51 nhắn tới sẽ không
> được phục vụ. Đừng phát link cho hàng trăm người rồi mới đọc dòng này.

---

## 2. Thêm bot vào nhóm

Đây là thứ **Zalo OA doanh nghiệp không làm được**, và là lý do nhiều người chọn
Bot Creator.

1. Copy **cùng cái link** ở trên
2. Dán vào nhóm chat
3. **Quản trị viên nhóm** bấm vào link
4. Bấm xác nhận **"Thêm Bot vào nhóm"**
5. Bot gửi một tin chào — thế là xong

Gói Basic được **3 nhóm**, và tính năng nhóm đang ở giai đoạn **beta**.

---

## 3. Nói chuyện với bot TRONG NHÓM — phần hay làm người ta bực nhất

Trong nhóm, bot **không đọc mọi tin nhắn**. Nó chỉ nhận được tin trong đúng hai
trường hợp:

| Cách | Làm thế nào |
|---|---|
| **@mention** | Gõ `@` rồi chọn tên bot trong danh sách |
| **Trả lời trực tiếp** | Nhấn giữ một tin **của bot** → *Trả lời* |

Ngoài hai cách đó, bot **không hề biết có ai vừa nói gì**. Nó không im lặng vì
hỏng — nó thật sự không nhận được tin.

Đây là thiết kế của Zalo, không phải của bot, và nó đúng ra là tốt: bot không đọc
lén toàn bộ chat nhóm.

### ⚠️ Gửi ảnh trong nhóm: phải tag bot NGAY TRÊN ảnh đó

Đây là cái bẫy làm nhiều người tưởng bot hỏng.

**Sai** — bot không nhận được ảnh:

> 1. Nhắn: `@Bot Gác Nhỏ xem giúp em cái này`
> 2. Rồi gửi ảnh ở tin **tiếp theo**

Tin thứ hai không có mention nào, nên bot **không bao giờ nhận được tấm ảnh**. Nó
chỉ thấy câu "xem giúp em cái này" mà chẳng có ảnh nào.

**Đúng** — gửi ảnh và **tag bot ngay trong phần chú thích của chính tấm ảnh**:

> Chọn ảnh → ở ô nhập chú thích, gõ `@` chọn tên bot → gửi

Nói cách khác: **mention phải nằm trong CÙNG tin nhắn với ảnh.**

Cách khác cũng chạy: **trả lời trực tiếp** một tin của bot rồi đính ảnh vào chính
tin trả lời đó.

> *Chi tiết này **đo từ thực tế**, không có trong tài liệu chính thức của Zalo —
> tài liệu chỉ nói về tin nhắn chữ. Nó suy ra đúng từ luật "bot chỉ nhận tin khi
> được mention hoặc được trả lời", nhưng Zalo có thể đổi.*

---

## 4. Nói chuyện với bot trong CHAT RIÊNG

Đơn giản hơn nhiều: **cứ nhắn bình thường.** Không cần tag, không cần cú pháp,
không có lệnh nào cả.

Gửi ảnh cũng gửi bình thường.

---

## 5. Đoạn văn dán sẵn cho nhóm

Copy nguyên đoạn dưới, sửa tên bot, rồi dán vào nhóm sau khi thêm bot. Ghim lại
càng tốt.

```
Nhóm mình vừa có thêm trợ lý ảo, mọi người dùng thế nào ạ:

• Hỏi gì thì gõ @ rồi chọn tên bot, ví dụ:
  @Tên Bot cho em hỏi giá loại A

• Gửi ảnh thì nhớ tag bot NGAY TRONG phần chú thích của tấm ảnh đó,
  đừng tag ở tin trước rồi mới gửi ảnh — bot sẽ không thấy ảnh.

• Hoặc nhấn giữ tin nhắn của bot rồi chọn "Trả lời" là bot cũng nhận được.

Bot chỉ đọc tin nào tag nó thôi, không đọc cả nhóm.
Cái gì bot chưa biết thì nó sẽ nói thật và chuyển cho người phụ trách.
```

---

## 6. Nhắc nhở cho người quản lý bot

**Bot không nhắn trước cho ai được.** Zalo không cho tra `chat_id` từ số điện
thoại, nên khách phải **nhắn trước** hoặc **bấm link** thì mới có cuộc trò chuyện.
Xem [`02-gioi-han-zalo.md`](02-gioi-han-zalo.md).

**Bot ghi lại câu nó không trả lời được** — kể cả trong nhóm. Đừng thêm bot vào
nhóm mà bạn không muốn nội dung được lưu.

**Xem bot còn thiếu gì:** nhắn *"báo cáo hôm nay"* cho bot trong chat riêng.

**Bảng điều khiển:** mini app Zalo Bot Creator có tab *Thông tin* (trạng thái,
tổng số người dùng) và tab *Chia sẻ* (link). Chi tiết ở
[`01-noi-zalo.md`](01-noi-zalo.md).

---

**Bot phải luôn bật thì khách nhắn mới tới nơi** — tin gửi lúc bot tắt là mất
hẳn. Xem [`07-cho-bot-chay-24-7.md`](07-cho-bot-chay-24-7.md).

---

*Nguồn: [tài liệu Zalo Bot — tương tác với nhóm](https://docs.zaloplatforms.com/docs/BOT/best-practices/build-bot-interaction-with-group).
Phần về ảnh trong nhóm là quan sát thực tế, chưa có trong tài liệu chính thức.*
