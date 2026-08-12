# Cài đặt — Windows và macOS

Bạn chỉ cần cài **một thứ duy nhất: `uv`**. Nó tự lo Python và mọi thư viện.

---

## Windows

Mở **PowerShell** (bấm Start, gõ "PowerShell"):

```powershell
winget install astral-sh.uv
```

Đóng PowerShell, mở lại. Kiểm tra:

```powershell
uv --version
```

---

## macOS

Mở **Terminal** (bấm `Cmd + Space`, gõ "Terminal"):

```bash
brew install uv
```

Chưa có Homebrew thì cài `uv` trực tiếp:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Đóng Terminal, mở lại. Kiểm tra:

```bash
uv --version
```

---

## Cài thư viện của dự án

Vào thư mục vừa tải về, rồi (giống nhau trên cả hai hệ):

```bash
uv sync
```

Lần đầu mất khoảng 1–2 phút. Nó tự tải Python 3.12 nếu máy chưa có.

---

## Kiểm tra mọi thứ ổn

```bash
uv run pytest -q
```

Dòng cuối phải là **`... passed`**, không có chữ `failed`. Có test đỏ thì đừng đi
tiếp — báo lại, đừng sửa bừa.

```bash
uv run agent-cskh check
```

Nó liệt kê những việc còn thiếu. Kho tri thức chưa có gì thì báo đỏ là **đúng** —
phần đó do bước phỏng vấn điền vào.

---

## Chạy

```bash
uv run agent-cskh chat
```

Không cần token Zalo, không cần API key, không tốn đồng nào.

---

## Dùng coding agent nào cũng được

Repo này không thiên vị công cụ nào. Mỗi công cụ tự tìm được hướng dẫn theo quy
ước riêng của nó, và cả ba đều dẫn về **cùng một file**.

| Công cụ | Nó tự đọc file | Câu bạn gõ |
|---|---|---|
| Claude Code | `CLAUDE.md` | `Đọc HUONG-DAN-AGENT.md và dựng bot cho tôi.` |
| Codex | `AGENTS.md` | như trên |
| Cursor | `AGENTS.md` | như trên |

Nội dung thật nằm ở `HUONG-DAN-AGENT.md`, kịch bản phỏng vấn ở `PHONG-VAN.md` —
cả hai đều ở gốc repo. **Không có gì bị giấu trong `.claude/`.**

### Riêng cho Codex

Cài (cần Node.js):

```bash
npm install -g @openai/codex
```

Rồi vào thư mục repo và chạy `codex`.

Ba điều nên biết trước:

**Nó sẽ xin phép liên tục.** Codex mặc định hỏi trước mỗi lần ghi file hay chạy
lệnh. Dựng bot cần ghi kha khá file, nên bạn sẽ bấm đồng ý nhiều lần — đó là bình
thường, không phải nó bị lỗi. Muốn đỡ phiền thì chọn chế độ cho phép ghi trong
thư mục làm việc ngay từ đầu.

**Đừng cho nó quyền chạy mọi thứ không hỏi.** Cám dỗ là bật chế độ tự động hoàn
toàn cho nhanh. Đừng — bước phỏng vấn *cần* nó dừng lại hỏi bạn, đó là cả điểm
mấu chốt.

**Nó tới `PHONG-VAN.md` qua ba chặng.** Khác Claude Code, Codex không quét thư mục
skill. Nó đi `AGENTS.md` → `HUONG-DAN-AGENT.md` → rồi mới tới `PHONG-VAN.md`.
Chuỗi đó chạy được, nhưng nếu có lúc nào thấy nó nhảy thẳng vào viết file thì
nhắc một câu là đủ:

> Đọc PHONG-VAN.md rồi hỏi tôi từng câu một.

> **Đã chạy thử thật (12/08/2026).** Codex tự đi hết chuỗi trên và **tự hỏi từng
> câu một** mà không cần nhắc. Không vấp chỗ nào.
>
> Vẫn còn hai thứ chưa ai kiểm: chạy trên **macOS**, và nối **Zalo thật**. Bạn là
> người đầu tiên làm thì gặp gì lệch, sửa lại giúp file này.

---

## Bảng đối chiếu lệnh

| Việc | Windows | macOS |
|---|---|---|
| Cài `uv` | `winget install astral-sh.uv` | `brew install uv` |
| Tạo file `.env` | `Copy-Item .env.example .env` | `cp .env.example .env` |
| Chạy có giám sát | `.\run.ps1` | `chmod +x run.sh` rồi `./run.sh` |
| Tự chạy khi bật máy | `.\scripts\cai_tu_khoi_dong.ps1` | `./scripts/cai_tu_khoi_dong.sh` |
| Mở file `.env` | Notepad | TextEdit |

Mọi lệnh `uv run ...` giống hệt nhau trên cả hai hệ.

---

## Còn cách nữa: Docker

Giống nhau trên mọi hệ điều hành, hợp khi máy khó chiều hoặc khi lên VPS:

```bash
docker compose up -d
```

Cần `.env` đã điền sẵn. Chi tiết: [05-chuyen-len-vps.md](05-chuyen-len-vps.md).
