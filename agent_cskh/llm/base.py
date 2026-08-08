"""Giao dien chung cho moi nha cung cap LLM.

Dinh dang tin nhan chuan la kieu Anthropic (khoi noi dung co cau truc) vi no bieu
dien duoc tool-use day du nhat; adapter Gemini chuyen doi sang dinh dang cua Google.
Them nha cung cap thu ba = viet mot class cai LLMProvider + mot dong trong router.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant"]
StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal", "error"]


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass(slots=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


@dataclass(slots=True)
class Msg:
    """Mot luot trong hoi thoai. Chi mot trong ba loai noi dung duoc dung."""

    role: Role
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: StopReason
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def wants_tools(self) -> bool:
        return self.stop_reason == "tool_use" and bool(self.tool_calls)


class LLMError(RuntimeError):
    def __init__(self, provider: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.retryable = retryable


class LLMProvider(ABC):
    """Mot nha cung cap. Phai khong co trang thai giua cac lan goi."""

    name: str
    model: str

    @abstractmethod
    async def complete(
        self,
        messages: list[Msg],
        *,
        system: str,
        system_theo_nguoi: str = "",
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 2048,
        timeout: float = 90.0,
    ) -> LLMResponse:
        """Goi model.

        `system` la khoi ON DINH — dung chung cho moi nguoi cung vai, duoc dat
        diem cache. `system_theo_nguoi` la phan rieng cua tung nguoi (ten hien
        thi, ngu canh hoc vien) va KHONG duoc cache: nhet no vao khoi on dinh se
        lam cache vo theo tung nguoi dung.
        """
        ...

    def _cost(self, input_tokens: int, output_tokens: int, cache_read: int = 0) -> float:
        """Uoc tinh chi phi USD. Ghi de o tung provider."""
        return 0.0
