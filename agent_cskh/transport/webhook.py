"""Nhan su kien qua webhook.

Vi sao day la duong chinh chu khong phai phuong an du phong: ngay 05/08/2026,
getUpdates cua Zalo tra 504/502 lien tuc (22 lan goi trong 2 phut khi CO tin
dang cho: 21x504, 1x502). Long-polling khong dung duoc.

Lop nay cung ghi lai NGUYEN VAN moi payload vao tests/fixtures/updates/ —
day chinh la cong cu kham pha schema ma dump_update.py da khong lam duoc.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.transport.base import InboundEvent, Transport
from agent_cskh.transport.normalize import normalize
from agent_cskh.transport.zalo_client import ZaloAPIError, ZaloClient

log = get_logger(__name__)

# Zalo chua cong bo ten header mang secret_token. Chap nhan moi ten hay gap
# va ghi log toan bo header o lan dau de biet chinh xac.
SECRET_HEADERS = (
    "x-bot-api-secret-token",
    "x-zalo-bot-secret-token",
    "x-secret-token",
    "secret-token",
)

QUEUE_MAX = 256


class WebhookTransport(Transport):
    def __init__(
        self,
        settings: Settings,
        client: ZaloClient,
        *,
        host: str = "127.0.0.1",
        port: int = 8080,
        public_url: str | None = None,
        capture: bool = True,
    ) -> None:
        self._s = settings
        self._client = client
        self._host = host
        self._port = port
        self._public_url = (public_url or settings.webhook_url).rstrip("/")
        self._capture = capture
        self._captured = 0
        self._logged_headers = False

        self._queue: asyncio.Queue[InboundEvent] = asyncio.Queue(maxsize=QUEUE_MAX)
        self._server: uvicorn.Server | None = None
        self._server_task: asyncio.Task[None] | None = None
        self._running = False

        self._app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        self._app.middleware("http")(self._log_every_request)
        self._app.post("/webhook")(self._on_update)
        # Zalo co the goi GET de xac minh URL truoc khi day tin. Neu chi khai bao
        # POST thi GET nhan 405 va Zalo co the coi webhook la hong roi im lang.
        self._app.get("/webhook")(self._on_verify)
        self._app.get("/health")(self._on_health)
        # Bat moi duong dan/phuong thuc con lai de khong bo sot request nao cua Zalo.
        self._app.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "HEAD", "OPTIONS"],
        )(self._on_catch_all)

    async def _log_every_request(self, request: Request, call_next):  # noqa: ANN001
        """Ghi lai MOI request. Day la cach duy nhat biet Zalo co go cua hay khong."""
        log.info(
            "http_den",
            method=request.method,
            path=request.url.path,
            ip=request.headers.get("cf-connecting-ip")
            or (request.client.host if request.client else "?"),
            ua=request.headers.get("user-agent", "?")[:60],
        )
        return await call_next(request)

    async def _on_verify(self) -> dict[str, Any]:
        """Tra 200 cho moi lan Zalo kiem tra URL."""
        return {"message": "Success"}

    async def _on_catch_all(self, request: Request, path: str) -> Response:
        log.warning("request_duong_dan_la", method=request.method, path=f"/{path}")
        return JSONResponse({"message": "Success"}, status_code=200)

    # ---------- HTTP ----------
    async def _on_health(self) -> dict[str, Any]:
        return {"ok": True, "queued": self._queue.qsize(), "captured": self._captured}

    async def _on_update(self, request: Request) -> Response:
        raw = await request.body()

        if not self._verify(request):
            log.warning("webhook_sai_secret", client=request.client.host if request.client else "?")
            return Response(status_code=403)

        if not self._logged_headers:
            self._logged_headers = True
            log.info("webhook_header_lan_dau", headers=dict(request.headers))

        try:
            body = json.loads(raw)
        except ValueError:
            log.warning("webhook_body_khong_phai_json", size=len(raw))
            return JSONResponse({"message": "Success"}, status_code=200)

        self._save_sample(body)

        event = normalize(body)
        if event is None:
            log.warning("webhook_khong_chuan_hoa_duoc", raw=body)
            return Response(status_code=200)
        if event.is_bot:
            return Response(status_code=200)

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            log.error("hang_doi_webhook_day", chat_id=event.chat_id[:8])
            return Response(status_code=200)

        log.info("nhan_su_kien", summary=event.summary())
        # Tra 200 ngay. Xu ly di theo hang doi, khong bat Zalo cho.
        # Body dung dung mau trong tai lieu Zalo: res.json({ message: "Success" }).
        return JSONResponse({"message": "Success"}, status_code=200)

    def _verify(self, request: Request) -> bool:
        secret = self._s.webhook_secret.get_secret_value()
        if not secret:
            return True
        for name in SECRET_HEADERS:
            if request.headers.get(name) == secret:
                return True
        # Mot so nen tang gui qua query string.
        return request.query_params.get("secret_token") == secret

    def _save_sample(self, body: dict[str, Any]) -> None:
        """Ghi payload tho — tra loi cac an so con lai ve schema Zalo."""
        if not self._capture or self._captured >= 40:
            return
        try:
            result = body.get("result") if isinstance(body.get("result"), dict) else body
            msg = result.get("message") if isinstance(result, dict) else None
            kind = "unknown"
            if isinstance(msg, dict):
                event_name = str(result.get("event_name") or "")
                kind = event_name.split(".")[1] if "." in event_name else "unknown"
            self._captured += 1
            stamp = datetime.now(tz=UTC).strftime("%H%M%S")
            path = self._s.fixtures_dir / f"wh-{self._captured:02d}-{kind}-{stamp}.json"
            path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info("da_luu_mau_payload", file=path.name, keys=sorted(msg or {}))
        except OSError as e:
            log.warning("khong_luu_duoc_mau", error=str(e))

    # ---------- Transport ----------
    async def start(self) -> None:
        if not self._public_url:
            raise RuntimeError(
                "Chua co WEBHOOK_URL. Chay cloudflared de lay dia chi HTTPS cong khai."
            )

        config = uvicorn.Config(
            self._app,
            host=self._host,
            port=self._port,
            log_level="info",
            access_log=True,
        )
        self._server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(self._server.serve())

        # Cho uvicorn san sang truoc khi bao Zalo tro toi day.
        for _ in range(50):
            if self._server.started:
                break
            await asyncio.sleep(0.1)
        if not self._server.started:
            raise RuntimeError("uvicorn khong khoi dong duoc")

        endpoint = f"{self._public_url}/webhook"
        secret = self._s.webhook_secret.get_secret_value()
        result = await self._client.set_webhook(endpoint, secret)
        log.info("da_dat_webhook", url=endpoint, result=result)

        self._running = True

    async def stop(self) -> None:
        self._running = False
        try:
            await self._client.delete_webhook()
        except ZaloAPIError as e:
            log.debug("delete_webhook_bo_qua", error=str(e))
        if self._server is not None:
            self._server.should_exit = True
        if self._server_task is not None:
            try:
                await asyncio.wait_for(self._server_task, timeout=10)
            except (TimeoutError, asyncio.CancelledError):
                self._server_task.cancel()
        log.info("webhook_dung")

    async def stream(self) -> AsyncIterator[InboundEvent]:
        while self._running or not self._queue.empty():
            try:
                async with asyncio.timeout(1.0):
                    event = await self._queue.get()
            except TimeoutError:
                continue
            yield event
