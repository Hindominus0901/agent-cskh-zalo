"""May chu cho widget chat tren website.

Kenh nay khac Zalo o mot diem quyet dinh moi thu con lai: **khach vo danh**.

Tren Zalo, `user_id` do Zalo cap va on dinh — nho no ma he phan quyen hai tang
biet ai la chu shop, ai la nhan vien, ai la khach. Tren web khong co gi tuong
duong. Ta phat mot id ngau nhien trong cookie, va id do:

  - khach xoa cookie la mat
  - khach tu sua duoc
  - hai nguoi dung chung may thi trung nhau

Vi vay khach web LUON o vai `stranger`. Dieu do nghe nhu mot han che, nhung no
chinh la cau tra loi dung: khach web chi doc duoc `wiki/public/`, khong bao gio
cham toi `wiki/internal/` (gia von, quy trinh noi bo). Khong co duong nao de
"nang quyen" tu web — va do la co y.

Moi thu khac — ba lop guard, kho tri thuc, ky nang, cong cu — chay y nguyen.
"""

from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Cookie, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from agent_cskh.config import Settings
from agent_cskh.harness.dispatcher import TurnDispatcher
from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database
from agent_cskh.transport.base import InboundEvent
from agent_cskh.web.chan import MSG_QUA_NHANH, MSG_QUA_TAI, NhipIP, TranNgay
from agent_cskh.web.khach import KhachWeb

log = get_logger(__name__)

TEN_COOKIE = "agent_cskh_phien"
THU_MUC = Path(__file__).parent
MAX_KY_TU_VAO = 1000

MSG_LOI = "Dạ em đang gặp trục trặc kỹ thuật ạ. Anh/chị nhắn lại giúp em một chút nữa nhé."
MSG_LAU = (
    "Dạ câu này em cần tra hơi lâu ạ. Anh/chị chờ em thêm chút "
    "hoặc để lại số điện thoại, bên em gọi lại ngay ạ."
)


class TinNhanVao(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_KY_TU_VAO)
    trang: str | None = Field(default=None, max_length=500)


def _ip(request: Request) -> str:
    """IP that cua khach.

    Sau reverse proxy (nginx, Cloudflare) thi `request.client.host` luon la IP
    cua proxy — moi khach tren doi se dung chung mot gau token. Doc
    `X-Forwarded-For` de tranh dieu do.

    CANH BAO: header nay khach TU DAT DUOC neu may chu phoi thang ra internet.
    Chi tin no khi co proxy dung truoc. Day cung la ly do `TranNgay` ton tai —
    no khong dua vao IP nen khong lua duoc.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


def tao_app(
    settings: Settings,
    *,
    dispatcher: TurnDispatcher,
    khach: KhachWeb,
    db: Database,
) -> FastAPI:
    app = FastAPI(title="Agent CSKH — kênh web", docs_url=None, redoc_url=None)
    nhip = NhipIP(settings.web_nhip_ip_moi_phut)
    tran = TranNgay(settings, db)

    goc_cho_phep = set(settings.web_origins)

    def _cors(resp: Response, origin: str | None) -> None:
        """Chi mo cho ten mien da khai bao.

        Khong dung `CORSMiddleware` voi `*`: mo cho ca internet nghia la trang
        bat ky cung nhung duoc widget nay va tinh phi API vao tai khoan chu shop.
        """
        if origin and origin in goc_cho_phep:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Vary"] = "Origin"

    @app.get("/health")
    async def health() -> dict[str, object]:
        st = await tran.trang_thai()
        return {"ok": True, "che_do": settings.che_do, "hom_nay": st.da_dung, "tran": st.tran}

    @app.options("/api/chat")
    async def chat_options(request: Request) -> Response:
        resp = Response(status_code=204)
        _cors(resp, request.headers.get("origin"))
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "content-type"
        return resp

    @app.post("/api/chat")
    async def chat(
        request: Request,
        tin: TinNhanVao,
        agent_cskh_phien: str | None = Cookie(default=None),
    ) -> Response:
        origin = request.headers.get("origin")
        if origin and origin not in goc_cho_phep:
            log.warning("web_chan_origin", origin=origin)
            return JSONResponse({"loi": "origin không được phép"}, status_code=403)

        # --- Phien ---
        phien_moi = not agent_cskh_phien or not _hop_le(agent_cskh_phien)
        phien = uuid.uuid4().hex if phien_moi else str(agent_cskh_phien)

        def _tra(cac_cau: list[str], ma: int = 200) -> Response:
            resp = JSONResponse({"tra_loi": cac_cau}, status_code=ma)
            _cors(resp, origin)
            if phien_moi:
                resp.set_cookie(
                    TEN_COOKIE,
                    phien,
                    max_age=30 * 86400,
                    httponly=True,
                    samesite="none" if origin else "lax",
                    secure=bool(origin),
                    path="/",
                )
            return resp

        # --- Chan lam dung: dem TRUOC khi phuc vu ---
        # Dem ca luot bi tu choi, neu khong ke cao bi chan van thu lai vo han
        # ma khong bao gio cham tran.
        await tran.dem(1)

        if not await nhip.cho_phep(_ip(request)):
            return _tra([MSG_QUA_NHANH], 429)
        if not await tran.cho_phep():
            return _tra([MSG_QUA_TAI], 503)

        await db.execute(
            "INSERT INTO web_phien (phien_id, tao_luc, gap_cuoi, ip_dau, trang) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(phien_id) DO UPDATE SET gap_cuoi = excluded.gap_cuoi",
            (phien, _bay_gio(), _bay_gio(), _ip(request), (tin.trang or "")[:500]),
        )

        # --- Dung su kien chuan, y het mot tin Zalo ---
        chat_id = f"web:{phien}"
        su_kien = InboundEvent(
            event_id=f"web-{secrets.token_hex(12)}",
            event_name="web.message",
            kind="text",
            chat_id=chat_id,
            chat_type="private",
            user_id=chat_id,
            display_name="Khách website",
            is_bot=False,
            text=tin.text.strip(),
            photo=None,
            voice_url=None,
            sticker=None,
            sent_at=None,
            received_at=datetime.now(tz=UTC),
            raw={"kenh": "web", "trang": tin.trang},
        )

        hop = khach.mo_hop(chat_id)
        try:
            xong = asyncio.Event()
            await dispatcher.submit(su_kien, xong)
            try:
                await asyncio.wait_for(xong.wait(), timeout=settings.web_cho_giay)
            except TimeoutError:
                log.warning("web_luot_qua_lau", chat_id=chat_id[:12])
                return _tra(hop.cac_cau or [MSG_LAU])
            return _tra(hop.cac_cau or [MSG_LOI])
        finally:
            khach.dong_hop(chat_id)

    @app.get("/widget.js")
    async def widget(request: Request) -> Response:
        js = (THU_MUC / "widget.js").read_text(encoding="utf-8")
        # Widget goi ve dung may chu da phuc vu no — khong phai cau hinh tay.
        js = js.replace("__GOC__", str(request.base_url).rstrip("/"))
        resp = PlainTextResponse(js, media_type="application/javascript")
        resp.headers["Cache-Control"] = "public, max-age=300"
        resp.headers["Access-Control-Allow-Origin"] = "*"  # file tinh, khong co du lieu
        return resp

    @app.get("/")
    async def demo() -> HTMLResponse:
        return HTMLResponse((THU_MUC / "demo.html").read_text(encoding="utf-8"))

    return app


def _hop_le(phien: str) -> bool:
    return len(phien) == 32 and all(c in "0123456789abcdef" for c in phien)


def _bay_gio() -> str:
    return datetime.now(tz=UTC).isoformat()
