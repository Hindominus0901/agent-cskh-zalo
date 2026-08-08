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

Phải thấy khoảng **355 test xanh**. Có test đỏ thì đừng đi tiếp — báo lại, đừng
sửa bừa.

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
