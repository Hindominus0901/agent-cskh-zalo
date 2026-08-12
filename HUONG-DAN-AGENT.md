# Hướng dẫn cho coding agent

> Đây là **nguồn sự thật duy nhất** cho mọi coding agent — Claude Code, Codex,
> Cursor, hay bất cứ agent nào khác. `CLAUDE.md` và `AGENTS.md` chỉ là hai cái
> biển chỉ đường về đây, để mỗi công cụ tìm được nó theo quy ước riêng của mình.
>
> Sửa hướng dẫn thì sửa ở file này. Đừng chép nội dung sang chỗ khác — hai bản
> lệch nhau là nguồn lỗi.

Bạn đang cầm một **template**, không phải một dự án đã xong.

Việc của bạn **không phải** đọc hiểu rồi sửa code. Việc của bạn là **phỏng vấn
người đang ngồi cạnh** rồi dựng con bot của chính họ. Code đã chạy được rồi.

Người đó nhiều khả năng không biết lập trình. Đừng hỏi họ câu kỹ thuật nào ngoài
những câu ở bước B0.

---

## Ba điều tuyệt đối không được làm

Đọc kỹ ba mục này trước khi gõ lệnh đầu tiên. Chúng là lý do template này tồn tại.

### 1. Không được bịa nội dung kinh doanh

Một trang trong `knowledge/` chỉ được viết từ **câu trả lời nguyên văn** của chủ
doanh nghiệp. Chưa hỏi thì chưa viết — ghi `[CHỜ HỌC VIÊN: ...]` vào đúng chỗ đó
rồi hỏi.

Kiến thức chung về ngành nghe rất hợp lý, và đúng ở phần lớn trường hợp. Nhưng
thứ làm hỏng việc luôn là **số liệu riêng của họ**: giá của họ, chính sách đổi
trả của họ, thời gian giao hàng của họ. Một trang bảng giá bạn tự suy ra sẽ được
bot đọc cho khách thật nghe, bằng giọng rất tự tin.

Không có "giá tham khảo". Không có "thông thường các shop hay...". Không có
placeholder trông giống thật.

### 2. Không được bỏ bước phỏng vấn

Không suy ra ngành nghề từ tên thư mục, từ vài câu chat, hay từ file có sẵn trên
máy. Phải hỏi.

Hỏi **từng câu một**, đợi trả lời rồi mới hỏi câu tiếp. Đừng dán cả bảng câu hỏi
một lần: bạn sẽ nhận về một câu trả lời gộp, và câu trả lời gộp **luôn bỏ qua
câu khó nhất** — thường lại là câu quan trọng nhất.

### 3. Không được tự ý bật chế độ `ai`

Mặc định là `CHE_DO=tra_cuu` — chạy 0 đồng, không cần API key.

Chỉ đổi sang `ai` khi chủ doanh nghiệp **nói rõ** rằng họ đã có
`ANTHROPIC_API_KEY` và chấp nhận trả tiền theo lượt. Đừng gợi ý đổi khi họ chưa
thấy bot chạy.

---

## Làm theo đúng thứ tự. Không nhảy bước.

### B0 — Nhận diện máy trước

**Hỏi hoặc tự phát hiện: Windows hay macOS.** Rồi chỉ đưa lệnh của hệ đó. Đưa
lệnh PowerShell cho người dùng Mac là lỗi hay gặp nhất, và nó làm người ta mất
niềm tin ngay ở phút đầu.

| | Windows | macOS |
|---|---|---|
| Cài `uv` | `winget install astral-sh.uv` | `brew install uv` |

`uv` tự lo Python 3.12, không cần cài Python riêng.

### B1 — Dựng và kiểm tra khung

```bash
uv sync
uv run pytest -q
```

Test phải **xanh hết** — dòng cuối không được có chữ `failed`. Đừng đếm số
test, con số đó đổi mỗi lần ai thêm test.

**Đỏ thì dừng lại và báo** — đừng sửa bừa.
Test đỏ ở đây nghĩa là môi trường có vấn đề, không phải template có vấn đề.

### B2 — Phỏng vấn

Đọc **`PHONG-VAN.md`** (nằm ngay ở gốc repo này) và làm đúng theo đó.

Đó là 17 câu, chia bốn nhóm theo bốn trụ cột của một con bot. Hỏi từng câu một.

### B3 — Sinh kho tri thức

Từ câu trả lời — **và chỉ từ câu trả lời** — viết:

- `knowledge/persona.md` (thay hết chỗ `[CHỜ HỌC VIÊN]`)
- các trang trong `knowledge/wiki/public/`, `hocvien/`, `internal/`

Đọc `knowledge/CLAUDE.md` trước khi viết trang đầu tiên. Quan trọng nhất: trường
`summary` và trường `tu_khoa`.

Rồi dựng lại danh mục:

```bash
uv run python scripts/wiki_index.py
```

### B4 — Tự kiểm tra

```bash
uv run agent-cskh check
```

**Còn dòng `[THIẾU]` nào thì chưa xong.** Đừng báo với người dùng là đã dựng xong
khi bảng này còn đỏ.

### B5 — Thử bot bằng chính câu của họ

```bash
uv run agent-cskh chat
```

Gõ lại **5 câu mà chủ doanh nghiệp vừa kể là khách hay hỏi nhất**. Xem bot trả
lời có đúng không.

Cuối phiên, CLI in ra danh sách câu bot không trả lời được. Mỗi câu đó là một
trang còn thiếu — quay lại B3 viết thêm, rồi thử lại.

Chỉ khi bot trả lời được ít nhất 4/5 câu mới đi tiếp.

### B6 — Hỏi có muốn nối Zalo không

Chỉ hỏi sau khi B5 đạt. Muốn thì mở `docs/01-noi-zalo.md` và đi từng bước cùng họ.

Tạo bot trên Zalo chỉ mất khoảng 5 phút và **không phải chờ duyệt** — làm ngay
trong app Zalo qua OA *Zalo Bot Manager*, bằng tài khoản cá nhân.

**Đừng bảo họ đi đăng ký OA doanh nghiệp.** Đó là một sản phẩm khác của Zalo,
tốn cả ngày chờ duyệt và không cần cho template này.

---

## Những thứ không được sửa

Đây là các lớp bảo vệ. Chúng được viết sau khi đã có sự cố thật, và mỗi cái đều
có ghi chú giải thích ngay trong file.

| Đường dẫn | Nó chặn gì |
|---|---|
| `agent_cskh/security/` | phân quyền, hạn mức, giới hạn tốc độ |
| `agent_cskh/tools/base.py` — `ToolRegistry` | kiểm quyền hai tầng; từ chối thì báo "không có tool đó" chứ không báo "thiếu quyền" |
| `agent_cskh/harness/turn.py` — `_chan_*` | chặn trả lời không có căn cứ, chặn tự xác nhận đã nhận tiền |
| `agent_cskh/wiki/store.py` | quyền đọc đến từ **thư mục**, không từ nội dung file |
| `tests/test_authz.py`, `tests/test_wiki.py` | canh đúng những thứ trên |

Nếu một test trong `tests/test_authz.py::TestCachLyQuyen` hay `tests/test_wiki.py`
chuyển đỏ: **dừng lại, sửa cho xanh trước khi làm bất cứ việc gì khác.** Đỏ ở đó
nghĩa là tài liệu nội bộ đang rò ra cho khách.

`tests/test_authz.py::TestPersonaCoDuThanhPhan` canh riêng việc bạn viết lại
`persona.md`. Nó kiểm tra các dòng ràng buộc an toàn còn nguyên. Nếu nó đỏ sau
khi bạn sửa persona, bạn vừa xoá mất một ràng buộc — thêm lại, đừng sửa test.

---

## Khi nào phải dừng lại và hỏi

- Chủ doanh nghiệp trả lời mơ hồ ở câu về **giá** hoặc câu về **điều tuyệt đối
  không được nói**. Hai câu này sinh thẳng ra lớp chặn; đoán sai là bot nói sai
  với khách thật.
- Họ muốn bot làm một việc mà template chưa có công cụ (đặt hàng, tra đơn, tính
  tiền). Nói rõ là chưa có, đừng giả vờ có.
- Họ đưa dữ liệu khách hàng thật để bạn nhập vào. Hỏi lại xem có cần thật không.
- Test đỏ mà bạn không hiểu vì sao.

---

## Hai điều về file

**Không tạo `.env` chứa giá trị thật thay họ.** Copy `.env.example` thành `.env`
rồi để họ tự dán token và key vào. `.env` đã nằm trong `.gitignore` — đừng bao
giờ gỡ nó ra.

**`knowledge/` được git theo dõi, và đó là có chủ đích.** Nhân viên sửa được kho
tri thức từ điện thoại (chỉ cần nhắn “thêm trang …”), nên git là đường lùi duy nhất. Nếu
sau này thêm remote GitHub, repo phải để **private** — `wiki/internal/` chứa
thông tin nội bộ.
