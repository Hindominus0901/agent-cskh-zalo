# Kịch bản phỏng vấn — dựng bot cho một doanh nghiệp

> Đây là bước **B2** trong [HUONG-DAN-AGENT.md](HUONG-DAN-AGENT.md). Đọc file đó
> trước nếu bạn chưa đọc.
>
> File này dùng chung cho mọi coding agent. Claude Code tìm được nó qua
> `.claude/skills/khoi-tao/`; Codex và Cursor thì đọc thẳng từ đây.

Nguyên tắc gốc: **mỗi dòng trong kho tri thức phải truy được về một câu người
chủ đã nói ra.** Không truy được thì không viết.

Một con bot có bốn trụ cột. Bộ câu hỏi này chia đúng theo bốn trụ đó, và mỗi câu
ghi rõ nó sinh ra file nào.

| Trụ cột | Câu | Sinh ra |
|---|---|---|
| System prompt (bot là ai, nói thế nào) | 1–5 | `knowledge/persona.md` |
| Kho kiến thức (bot biết gì) | 6–10 | `knowledge/wiki/**` |
| Công cụ (bot làm được gì) | 11–14 | `.env`, ghi chú cho sau |
| Skill (bot làm theo quy trình nào) | 15–17 | `skills/**` |

## Các bước

**1. Hỏi từng câu một. Đây là luật, không phải gợi ý.**

Đợi trả lời rồi mới hỏi câu tiếp. Dán cả bảng câu hỏi một lần sẽ nhận về một câu
trả lời gộp, và câu trả lời gộp **luôn bỏ qua câu khó nhất** — mà câu khó nhất
thường là câu 2, câu 4 và câu 6, tức là ba câu đáng giá nhất.

Nếu họ trả lời gộp nhiều câu, cứ nhận, nhưng **quay lại hỏi riêng những câu họ
lướt qua**.

**2. Hỏi trước hai câu kỹ thuật để rẽ nhánh.**

> **0a.** Anh/chị đã tạo bot trên Zalo chưa ạ?

Chưa có → nói luôn cho họ yên tâm: **chỉ mất khoảng 5 phút và không phải chờ
duyệt gì cả**. Tạo ngay trong app Zalo, tìm OA *Zalo Bot Manager* rồi chọn
"Tạo bot" — dùng tài khoản Zalo cá nhân là được, **không cần OA doanh nghiệp**.

Đừng để họ đi xin OA doanh nghiệp: đó là một sản phẩm khác, tốn cả ngày chờ duyệt
và không cần cho template này. Xem `docs/01-noi-zalo.md`.

Dù sao thì cũng chưa cần token ngay bây giờ — cứ dựng kho tri thức và thử bằng
`agent-cskh chat` trước.

> **0b.** Mình chạy bản miễn phí trước, hay anh/chị muốn dùng bản AI luôn (tốn
> khoảng 60.000đ/tháng tiền API, cần thẻ quốc tế)?

Mặc định là bản miễn phí. **Đừng thuyết phục họ trả tiền khi chưa thấy bot chạy.**

**3. Nhóm 1 — Bot là ai và nói thế nào** → `knowledge/persona.md`

> **1.** Anh/chị bán gì ạ? Nói một câu như đang nói với người lạ.
>
> **2.** Khách của anh/chị là ai, và **điều họ lo nhất trước khi mua** là gì?
>
> **3.** Bot xưng hô thế nào — *em*, *mình*, hay *shop*? Gọi khách là *anh/chị*
> hay *bạn*?
>
> **4.** Có câu nào bot **tuyệt đối không được nói** không ạ? Ví dụ: tự chốt giá,
> hứa ngày giao hàng, xác nhận đã nhận được tiền.
>
> **5.** Khi nào thì bot **phải** chuyển ngay cho người thật, không được cố trả lời?

Câu 2 là câu đáng giá nhất cả buổi — nó quyết định bot nói gì ở câu thứ hai với
mọi khách. Họ trả lời hời hợt thì hỏi tiếp: *"lần gần nhất có khách hỏi mãi rồi
không mua, họ băn khoăn chuyện gì ạ?"*

Câu 4 và 5 sinh thẳng ra lớp chặn. Trả lời mơ hồ thì **dừng lại hỏi cho rõ** —
đừng đoán.

**4. Nhóm 2 — Bot biết gì** → `knowledge/wiki/`

> **6.** 10 câu khách hỏi nhiều nhất là gì ạ?
>
> **7.** Bảng giá / các gói của mình thế nào? Cái nào công khai được, cái nào không?
>
> **8.** Khách mua hàng thì đi qua những bước nào ạ?
>
> **9.** Chính sách đổi trả / bảo hành / hoàn tiền thế nào?
>
> **10.** Thông tin nào **khách không được biết** — chỉ nhân viên xem?

Câu 6 quan trọng hơn cả chín câu còn lại cộng lại. Mỗi câu họ kể ra là một trang
`public/`. Họ chỉ nghĩ ra 3–4 câu thì gợi ý theo nhóm: giá, giao hàng, chất
lượng, so sánh với chỗ khác, sau khi mua thì sao.

Với **mỗi trang**, hỏi thêm một câu bắt buộc:

> *"Khách thường hỏi câu này bằng những cách nói nào ạ?"*

Câu trả lời vào thẳng trường `tu_khoa`. Đây là thứ quyết định bản miễn phí chạy
được hay không: tìm kiếm là regex, nên "giá" khớp còn "mắc không", "bao nhiêu
xu", "có đắt không" thì trượt sạch nếu không có `tu_khoa`.

Câu 7 và 10 quyết định trang nằm ở `public/` hay `internal/`. **Phân vân thì để
`internal/`** — trang nội bộ đặt nhầm ra ngoài thì lộ, còn trang công khai đặt
nhầm vào trong chỉ làm bot trả lời thiếu, và cái đó lộ ra ngay ở báo cáo hàng ngày.

**5. Nhóm 3 — Bot làm được gì** → `.env` và ghi chú

> **11.** Khách để lại số điện thoại và nhu cầu thì anh/chị muốn lưu ở đâu, ai xem?
>
> **12.** Bot chuyển cho người thật thì chuyển cho ai ạ? (cần tên; `user_id` Zalo
> lấy sau bằng lệnh `/whoami`)
>
> **13.** Có cần bot nhắc lại khách sau vài ngày không?
>
> **14.** Bot có cần xem ảnh khách gửi không — biên lai chuyển khoản, ảnh sản phẩm?

Câu 13: template **chưa có** chức năng nhắn chủ động, và đó là chủ ý (xem README
mục "Chưa làm"). Họ cần thì ghi lại, đừng hứa là có.

**6. Nhóm 4 — Bot làm theo quy trình nào** → `skills/`

> **15.** Có việc nào bot phải làm **đúng thứ tự** không ạ? Ví dụ tư vấn size thì
> phải hỏi chiều cao, cân nặng rồi mới gợi ý.
>
> **16.** Có việc gì bot làm nhưng **phải anh/chị duyệt trước** không?
>
> **17.** Khách nhắn lần đầu, bot nên nói gì ạ?

**7. Viết file. Chỉ từ câu trả lời.**

Đọc `knowledge/CLAUDE.md` trước khi viết trang đầu tiên.

Chỗ nào họ chưa trả lời: ghi `[CHỜ HỌC VIÊN: câu hỏi cụ thể]` rồi quay lại hỏi.
**Không lấy kiến thức chung điền vào.**

**8. Dựng danh mục rồi tự kiểm.**

```bash
uv run python scripts/wiki_index.py
uv run agent-cskh check
```

**9. Thử bằng chính câu của họ.**

```bash
uv run agent-cskh chat
```

Gõ lại 5 trong 10 câu ở câu hỏi số 6. Bot trượt câu nào thì viết thêm trang cho
câu đó rồi thử lại.

## Xong khi

- `agent-cskh check` không còn dòng `[THIẾU]` nào
- `persona.md` không còn chữ `[CHỜ HỌC VIÊN]`
- Có ít nhất 5 trang wiki, **mọi trang đều có `summary` và `tu_khoa`**
- Bot trả lời đúng ít nhất 4 trong 5 câu thử ở bước 9
- Không một dòng nào trong `knowledge/` mà bạn không chỉ ra được người chủ đã
  nói câu đó lúc nào

## Bẫy hay gặp

- **Điền cho đủ chỗ trống.** Người chủ nói "cái này để sau" mà bạn vẫn viết một
  đoạn nghe hợp lý. Bot sẽ đọc đoạn đó cho khách thật nghe, bằng giọng rất tự
  tin. `[CHỜ HỌC VIÊN]` xấu, nhưng nó trung thực.

- **Hỏi gộp cho nhanh.** Tiết kiệm được năm phút và mất đúng ba câu quan trọng
  nhất.

- **Bỏ qua `tu_khoa` vì "tiêu đề nói rõ rồi".** Tiêu đề là chữ *bạn* viết,
  `tu_khoa` là chữ *khách* gõ. Hai thứ đó hiếm khi trùng nhau.

- **Viết trang dài.** Bot cắt ở 1400 ký tự khi trả lời. Một trang 3000 chữ tức
  là hơn nửa nội dung không bao giờ tới được khách. Tách thành nhiều trang nhỏ,
  mỗi trang trả lời đúng một câu hỏi.

- **Để mọi trang ở `public/` cho tiện.** Giá vốn, hoa hồng, kịch bản xử lý khách
  khó tính — những thứ này ở `public/` là bot sẽ đọc cho khách nghe.

- **Nói "xong rồi" khi `check` còn đỏ.** Người dùng không tự chạy lại lệnh đó
  đâu. Họ sẽ đem bot đi dùng thật.
