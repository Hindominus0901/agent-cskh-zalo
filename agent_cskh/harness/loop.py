"""Vong lap agent — tu InboundEvent den cau tra loi da gui.

Batch, khong streaming: Zalo khong co editMessageText nen khong the cap nhat dan
mot tin nhan. Tin hieu tien do duy nhat la sendChatAction("typing").

Phase 1 chua co tool nao duoc dang ky, nen vong lap thuong ket thuc ngay o vong
dau. Cau truc da san sang cho Phase 2 bat tool-calling that.
"""

from __future__ import annotations

import asyncio

from agent_cskh.harness import errors
from agent_cskh.harness.prompt import build_system
from agent_cskh.harness.turn import TurnContext
from agent_cskh.harness.typing_indicator import TypingKeepAlive
from agent_cskh.llm.base import LLMError, LLMResponse, Msg, ToolResult
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)


async def _ghi_chi_phi(ctx: TurnContext, resp: LLMResponse) -> None:
    """Ghi lai chi phi mot lan goi. Hong thi khong duoc lam hong ca luot.

    Dat o `_complete` vi day la cua DUY NHAT ma vong lap chinh goi model —
    ghi o tung cho goi thi som muon co mot duong quen mat, va bo dem se thap
    hon thuc te ma khong ai biet. Cung bai hoc voi quota Zalo hoi 07/08/2026:
    dem o bon cho khac nhau nen dem gap doi.
    """
    try:
        await ctx.repo.ghi_chi_phi(
            chat_id=ctx.chat_id,
            provider=resp.provider,
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            cache_read=resp.cache_read_tokens,
            cost_usd=resp.cost_usd,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("khong_ghi_duoc_chi_phi", error=str(e))


def _ghep_ngu_canh(*phan: str) -> str:
    """Ghep cac khoi ngu canh theo nguoi, bo khoi rong.

    Bo khoi rong la quan trong: nguoi la khong co khoi nao trong so nay, va mot
    chuoi "\\n\\n" thua van la mot chuoi khac — no lam vo diem cache o khoi theo
    nguoi.
    """
    return "\n\n".join(p for p in phan if p.strip())


class AgentLoop:
    def __init__(self) -> None:
        pass

    async def run_turn(self, ctx: TurnContext) -> None:
        try:
            async with asyncio.timeout(ctx.settings.turn_timeout):
                await self._run(ctx)
        except TimeoutError:
            log.warning("luot_qua_han", chat_id=ctx.chat_id[:8])
            await self._safe_reply(ctx, errors.MSG_QUA_LAU)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - lop chan cuoi cung
            log.exception(
                "loi_khong_luong_truoc_trong_luot",
                chat_id=ctx.chat_id[:8],
                error=str(e),
                raw=ctx.event.raw,
            )
            await self._safe_reply(ctx, errors.MSG_LOI_HE_THONG)

    # ---------- ben trong ----------
    async def _run(self, ctx: TurnContext) -> None:
        # File tai lieu khong bao gio den duoc — tra loi du phong ngay, khong ton token.
        if ctx.event.kind == "unsupported":
            await ctx.reply(errors.MSG_KHONG_DOC_DUOC_FILE)
            return

        async with TypingKeepAlive(ctx.client, ctx.chat_id):
            messages = await ctx.buffer.build(ctx.event)
            system, system_theo_nguoi = build_system(
                ctx.settings,
                ctx.principal,
                wiki=ctx.wiki,
                kho_skill=ctx.kho_skill,
                extra=_ghep_ngu_canh(
                    await ctx.bo_nho_da_biet(),
                ),
            )
            provider = ctx.router.choose(ctx.route_context())

            for i in range(ctx.settings.max_iterations):
                ctx.turn_index = i
                resp = await self._complete(ctx, provider, messages, system, system_theo_nguoi)

                if resp is None:
                    await ctx.reply(errors.MSG_LOI_HE_THONG)
                    return

                if resp.stop_reason == "refusal":
                    log.warning("model_tu_choi", provider=resp.provider)
                    await ctx.reply(errors.MSG_QUA_NHIEU_BUOC)
                    return

                if not resp.wants_tools:
                    await ctx.reply(resp.text or errors.MSG_LOI_HE_THONG)
                    return

                # --- Co tool call ---
                messages.append(
                    Msg(role="assistant", text=resp.text or None, tool_calls=resp.tool_calls)
                )
                results = await self._run_tools(ctx, resp)
                messages.append(Msg(role="user", tool_results=results))

                if ctx.escalation_signal:
                    provider = ctx.router.escalate(ctx.route_context())
                    ctx.escalation_signal = False

            log.warning("vuot_max_iterations", chat_id=ctx.chat_id[:8])
            await ctx.reply(errors.MSG_QUA_NHIEU_BUOC)

    async def _complete(
        self,
        ctx: TurnContext,
        provider,
        messages: list[Msg],
        system: str,
        system_theo_nguoi: str = "",
    ) -> LLMResponse | None:
        """Goi model, thu lai mot lan o muc thap neu loi la tam thoi.

        Moi duong ra khoi ham deu phai cham vao ctx.health_model — do la thu duy
        nhat cho scheduler biet model con song. Khoa API chet ma khong ai bao thi
        khach nhan cau du phong hang loat con ta khong hay biet gi (07/08/2026).
        """
        try:
            resp = await provider.complete(
                messages,
                system=system,
                system_theo_nguoi=system_theo_nguoi,
                tools=ctx.tools or None,
                max_tokens=2048,
                timeout=ctx.settings.llm_timeout,
            )
        except LLMError as e:
            ctx.health_model.ghi_loi(str(e))
            # Chi con mot nha cung cap, nen khong co duong ha xuong hang khac.
            # SDK anthropic da tu retry 429/5xx hai lan; den day ma van loi tam
            # thoi thi thu them dung mot lan o muc effort thap (nhanh hon, it
            # token hon) roi dung han.
            if e.retryable and provider is not ctx.router.fast:
                log.warning("thu_lai_o_muc_thap", loi=str(e))
                try:
                    resp2 = await ctx.router.fast.complete(
                        messages,
                        system=system,
                        system_theo_nguoi=system_theo_nguoi,
                        tools=ctx.tools or None,
                        max_tokens=2048,
                        timeout=ctx.settings.llm_timeout,
                    )
                except LLMError as e2:
                    ctx.health_model.ghi_loi(str(e2))
                    log.error("model_that_bai_ca_hai_lan", loi_dau=str(e), loi_sau=str(e2))
                    return None
                ctx.health_model.ghi_thanh_cong()
                # Lan thu lai cung ton tien — ghi `resp2`, khong phai `resp`.
                await _ghi_chi_phi(ctx, resp2)
                return resp2
            log.error("model_that_bai", error=str(e))
            return None

        ctx.health_model.ghi_thanh_cong()
        await _ghi_chi_phi(ctx, resp)
        return resp

    async def _run_tools(self, ctx: TurnContext, resp: LLMResponse) -> list[ToolResult]:
        """Chay song song. Tool loi tra ve is_error de model tu xoay, khong nem exception."""

        async def one(call) -> ToolResult:
            content, is_error = await ctx.registry.run(ctx, call.name, call.args)
            return ToolResult(call_id=call.id, content=content, is_error=is_error)

        return list(await asyncio.gather(*(one(c) for c in resp.tool_calls)))

    async def _safe_reply(self, ctx: TurnContext, text: str) -> None:
        """Gui cau du phong. Neu ca viec nay cung hong thi chi ghi log."""
        try:
            await ctx.reply(text)
        except Exception as e:  # noqa: BLE001
            log.error("khong_gui_duoc_cau_du_phong", chat_id=ctx.chat_id[:8], error=str(e))
