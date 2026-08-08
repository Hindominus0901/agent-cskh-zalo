"""Chinh sach dinh tuyen — toan bo policy nam gon trong mot ham.

Chi dung Claude. Router dinh tuyen giua hai muc `effort` thay vi hai nha cung cap:
  fast (effort=low)  — cau don gian, uu tien do tre. Khach Zalo bo di sau ~2 phut.
  deep (effort=high) — anh, viec nhieu buoc, cau mo ho, da qua 2 vong tool.

Lich su quyet dinh (05/08/2026): tung thiet ke hybrid Gemini Flash + Claude.
Bo Gemini vi hai ly do do duoc bang so lieu that:
  1. gemini-2.5-flash bi Google go bo giua chung (404 vinh vien) — rui ro van hanh.
  2. Gemini 3.x bat buoc tieu ~380 token suy nghi/luot, tinh gia token ra thanh
     ~$0.001/luot so voi ~$0.0017 cua Claude Sonnet 5. Re hon 40%, khong phai
     nhieu lan — khong bu noi chi phi nuoi hai nha cung cap va hai kieu loi.
Adapter Gemini van con trong lich su git neu can dung lai.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_cskh.config import Settings
from agent_cskh.llm.base import LLMProvider
from agent_cskh.llm.claude import ClaudeProvider
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class RouteContext:
    """Moi thu policy can biet ve mot luot. Harness dien vao."""

    text: str = ""
    has_image: bool = False
    is_stranger: bool = True
    needs_write_tools: bool = False
    turn_index: int = 0
    skill_model_hint: str | None = None
    skill_confidence: float = 0.0
    is_ambiguous: bool = False
    daily_cost_exceeded: bool = False


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._fast = ClaudeProvider(settings, effort="low")
        self._deep = ClaudeProvider(settings, effort="high")

    @property
    def fast(self) -> LLMProvider:
        return self._fast

    @property
    def deep(self) -> LLMProvider:
        return self._deep

    def choose(self, ctx: RouteContext) -> LLMProvider:
        if ctx.daily_cost_exceeded:
            return self._fast  # phanh tay
        if ctx.has_image:
            return self._deep  # bien lai, chung tu — doc sai la hong viec
        if ctx.skill_model_hint == "deep":
            return self._deep
        if ctx.turn_index >= 2:
            return self._deep  # da 2 vong tool -> viec kho
        if ctx.needs_write_tools:
            return self._deep  # ghi du lieu that -> khong duoc doan
        if ctx.is_ambiguous:
            return self._deep
        if len(ctx.text) < 200 and ctx.skill_confidence > 0.75:
            return self._fast
        return self._fast

    def escalate(self, ctx: RouteContext) -> LLMProvider:
        """Nang muc giua chung khi tool bao viec kho hon du kien."""
        log.info("nang_muc_effort", turn_index=ctx.turn_index)
        return self._deep
