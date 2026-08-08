"""Dinh nghia cong cu va so dang ky, co kiem soat quyen.

Nguyen tac: quyen duoc ep o TANG THUC THI. Model co the bi du do goi mot cong cu
nao do (prompt injection tu tin nhan khach hoac tu tai lieu), nhung neu principal
khong du quyen thi cong cu do khong ton tai trong danh sach gui len model, va ke
ca co goi thi registry cung tu choi chay.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_cskh.llm.base import ToolSpec
from agent_cskh.logging_setup import get_logger
from agent_cskh.security.whitelist import Role, role_at_least

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

Handler = Callable[["TurnContext", dict[str, Any]], Awaitable[str]]


@dataclass(slots=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Handler
    min_role: Role = "stranger"
    # Cong cu co ghi du lieu that (Notion, Sheets, lich...). Dung de router
    # day sang muc effort cao va de ghi audit.
    writes: bool = False
    # Luot co chay cong cu duoc lop chan pham vi coi la "luot co viec that" va
    # cho di qua. Dat False cho nhung cong cu KHONG chung minh duoc dieu do:
    #
    #   doc_trang / tim_trang  — goi vao mot trang khong ton tai van la mot lan
    #     goi. Thanh cong that duoc theo doi rieng, chinh xac hon, qua da_tra_kho.
    #   tim_hoi_thoai          — doc lai loi cu khong phai tra kho tri thuc.
    #   ghi_nho                — ghi chu ve nguoi dung khong tra loi duoc cau hoi.
    #
    # Bo sot mot cai o day la mo lai dung cai duong vong ma lop chan sinh ra de
    # bit: goi mot cong cu re tien bat ky, roi tra loi tu tri thuc chung.
    tinh_la_lam_viec: bool = True

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name, description=self.description, input_schema=self.input_schema
        )


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools or []:
            self.add(t)

    def add(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"cong cu trung ten: {tool.name}")
        self._tools[tool.name] = tool

    def allowed(self, role: Role) -> list[Tool]:
        return [t for t in self._tools.values() if role_at_least(role, t.min_role)]

    def specs(self, role: Role) -> list[ToolSpec]:
        return [t.spec() for t in self.allowed(role)]

    async def run(self, ctx: TurnContext, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Chay mot cong cu. Tra ve (noi_dung, la_loi).

        Khong bao gio nem exception ra ngoai — model tu xoay duoc khi nhan loi,
        nhung mot exception thoat ra se lam hong ca luot.
        """
        tool = self._tools.get(name)
        if tool is None:
            return f"Công cụ '{name}' không tồn tại.", True

        if not role_at_least(ctx.principal.role, tool.min_role):
            # Khong noi ro la "khong du quyen" — tranh lo su ton tai cua cong cu
            # noi bo cho nguoi la.
            log.warning("tu_choi_cong_cu", tool=name, role=ctx.principal.role, can=tool.min_role)
            return f"Công cụ '{name}' không tồn tại.", True

        t0 = time.monotonic()
        ok, err = True, None
        # Luot co chay cong cu la luot co viec that. Dung o lop chan pham vi de
        # khong phat oan nhung luot dang lam dung viec (luu lead, trich bien lai).
        # Khong phai cong cu nao cung tinh — xem ghi chu o `Tool.tinh_la_lam_viec`.
        if tool.tinh_la_lam_viec:
            ctx.da_chay_cong_cu = True
        try:
            # `tool_timeout` duoc khai bao trong config tu dau nhung KHONG AP O
            # DAU CA — phat hien 08/08/2026. Mot cong cu treo se an het 180 giay
            # cua ca luot, va khach chi thay bot im lang roi bao loi he thong.
            #
            # Cac cong cu hien tai deu tu co tran rieng (web_fetch 10s, model
            # 90s), nen tran nay la LUOI DO PHONG cho cong cu sau nay — nhat la
            # cau noi MCP, noi do tre nam o may nguoi khac.
            async with asyncio.timeout(ctx.settings.tool_timeout):
                return await tool.handler(ctx, args or {}), False
        except TimeoutError:
            ok, err = False, "qua han"
            log.error("cong_cu_treo", tool=name, giay=ctx.settings.tool_timeout)
            return (
                f"Công cụ '{name}' chạy quá lâu nên em dừng lại. "
                "Hãy nói thật với khách là chưa lấy được thông tin.",
                True,
            )
        except Exception as e:  # noqa: BLE001 - loi cong cu khong duoc lam hong luot
            ok, err = False, str(e)
            log.exception("cong_cu_loi", tool=name, error=str(e))
            return f"Công cụ '{name}' gặp lỗi: {e}", True
        finally:
            await _audit(ctx, tool, args, ok, err, int((time.monotonic() - t0) * 1000))


async def _audit(
    ctx: TurnContext,
    tool: Tool,
    args: dict[str, Any],
    ok: bool,
    err: str | None,
    ms: int,
) -> None:
    """Ghi lai moi lan goi cong cu. Bat buoc voi cong cu ghi du lieu."""
    try:
        await ctx.repo.log_tool_call(
            chat_id=ctx.chat_id,
            user_id=ctx.principal.user_id,
            tool_name=tool.name,
            args_json=json.dumps(args, ensure_ascii=False)[:1000],
            ok=ok,
            error=err,
            duration_ms=ms,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("khong_ghi_duoc_audit", error=str(e))


__all__ = ["Handler", "Tool", "ToolRegistry"]
