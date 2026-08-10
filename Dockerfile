# Anh chay cho VPS Linux. Xem docs/05-chuyen-len-vps.md.
#
# Hai quyet dinh dang noi:
#   - Chay bang user khong phai root. Bot doc noi dung tu nguoi la gui den, nen
#     neu co lo hong o dau do thi ke tan cong khong duoc quyen root.
#   - data/ va knowledge/ la volume. Toan bo trang thai (CSDL, kho tri thuc,
#     anh bien lai) nam ngoai container — go container di, du lieu con nguyen.

FROM python:3.12-slim-bookworm

# tzdata: log va scheduler chay theo gio Viet Nam.
# ca-certificates: goi HTTPS toi Zalo va Anthropic.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Ho_Chi_Minh \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Cai dependency truoc, tach khoi ma nguon — sua code khong phai cai lai thu vien.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY agent_cskh/ ./agent_cskh/
COPY scripts/ ./scripts/
# skills/ PHAI duoc chep vao. Quen no thi `KhoSkill.nap()` tra ve 0 va bot mat
# sach quy trinh — im lang, khong mot dong loi nao, chi la bot bong tra loi kem
# di. Khac `knowledge/` (la volume, nguoi dung tu gan), `skills/` di theo ma
# nguon vi no la mot phan cua san pham.
COPY skills/ ./skills/
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 bot \
    && mkdir -p /app/data /app/knowledge \
    && chown -R bot:bot /app
USER bot

# Webhook mo cong 8080. Che do polling khong dung cong nao.
EXPOSE 8080

# Kiem tra suc khoe: chi co y nghia o che do webhook. O che do polling thi
# container van duoc coi la khoe chung nao tien trinh con song.
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1

CMD ["python", "-m", "agent_cskh"]
