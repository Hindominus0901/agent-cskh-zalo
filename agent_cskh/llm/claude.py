"""Adapter Claude (Anthropic).

Luu y ve API Claude Sonnet 5 (da doi chieu tai lieu 05/08/2026):
  - `temperature` / `top_p` / `top_k` BI TU CHOI (400) — dieu huong bang prompt
  - `thinking={"type":"enabled","budget_tokens":N}` da bo — dung "adaptive"
  - Do sau suy nghi dieu khien bang output_config={"effort": ...}
  - thinking.display mac dinh "omitted"; ta khong hien thinking cho khach nen giu nguyen
  - Prompt cache: tien to toi thieu 1024 token voi Sonnet 5
"""

from __future__ import annotations

from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    NotFoundError,
    RateLimitError,
)

from agent_cskh.config import Settings
from agent_cskh.llm.anh import khoi_anh
from agent_cskh.llm.base import (
    LLMError,
    LLMProvider,
    LLMResponse,
    Msg,
    StopReason,
    ToolCall,
    ToolSpec,
)
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)

# USD tren 1 trieu token. Cache doc ~0.1x gia vao.
PRICE_IN = 3.00
PRICE_OUT = 15.00
PRICE_CACHE_READ = 0.30

_STOP_MAP: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "refusal": "refusal",
    "stop_sequence": "end_turn",
    "pause_turn": "tool_use",
}


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, settings: Settings, *, effort: str = "medium") -> None:
        self._s = settings
        self.model = settings.claude_model
        self._effort = effort
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_retries=2,
        )

    # ---------- chuyen doi dinh dang ----------
    async def _to_api(self, messages: list[Msg]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            blocks: list[dict[str, Any]] = []

            for url in m.image_urls:
                # TU TAI roi gui byte, khong dua URL de Anthropic tu tai.
                #
                # Kiem chung 08/08/2026: `source.type = "url"` tra HTTP 400 voi
                # MOI host thu qua, va placehold.co noi ro ly do — bo tai cua
                # Anthropic ton trong robots.txt. CDN Zalo chan crawler va URL
                # anh co chu ky, nen duong do khong bao gio chay duoc.
                #
                # Xem `agent_cskh/llm/anh.py`.
                if (khoi := await khoi_anh(url)) is not None:
                    blocks.append(khoi)
                else:
                    # KHONG am tham bo di. Model khong thay anh ma cung khong
                    # biet la co anh se tra loi lac de, va nguoi dung tuong bot
                    # dang phot lo minh.
                    blocks.append(
                        {
                            "type": "text",
                            "text": "[có một tấm ảnh ở đây nhưng không tải được — "
                            "hãy nói thật và xin gửi lại]",
                        }
                    )

            for res in m.tool_results:
                blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": res.call_id,
                        "content": res.content,
                        "is_error": res.is_error,
                    }
                )

            if m.text:
                blocks.append({"type": "text", "text": m.text})

            for call in m.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": call.args,
                    }
                )

            if blocks:
                out.append({"role": m.role, "content": blocks})
        return out

    def _cost(self, input_tokens: int, output_tokens: int, cache_read: int = 0) -> float:
        return (
            input_tokens * PRICE_IN + output_tokens * PRICE_OUT + cache_read * PRICE_CACHE_READ
        ) / 1_000_000

    # ---------- goi ----------
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
        # Chi khoi ON DINH duoc dat cache_control -> cac luot sau doc lai gia 0.1x.
        # Hieu luc khi tien to >= 1024 token; duoi nguong thi im lang khong cache.
        #
        # Phan theo tung nguoi PHAI nam o block sau, khong cache. Truoc 07/08/2026
        # ten hien thi Zalo nam chung trong khoi duoc cache, nen cache vo theo
        # tung nguoi dung — tra tien luu cache ma gan nhu khong bao gio doc lai.
        system_blocks: list[dict[str, Any]] = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        if system_theo_nguoi.strip():
            system_blocks.append({"type": "text", "text": system_theo_nguoi})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": await self._to_api(messages),
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self._effort},
        }
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]

        try:
            resp = await self._client.with_options(timeout=timeout).messages.create(**kwargs)
        except NotFoundError as e:
            raise LLMError(self.name, f"model khong ton tai: {self.model}") from e
        except RateLimitError as e:
            raise LLMError(self.name, "rate limit", retryable=True) from e
        except APIStatusError as e:
            raise LLMError(
                self.name, f"HTTP {e.status_code}", retryable=e.status_code >= 500
            ) from e
        except APIConnectionError as e:
            raise LLMError(self.name, "loi ket noi", retryable=True) from e

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, args=dict(block.input or {}))
                )

        stop = _STOP_MAP.get(resp.stop_reason or "", "end_turn")
        if stop == "refusal":
            log.warning(
                "claude_tu_choi",
                category=getattr(getattr(resp, "stop_details", None), "category", None),
            )

        usage = resp.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        return LLMResponse(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            stop_reason=stop,
            provider=self.name,
            model=resp.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cost_usd=self._cost(usage.input_tokens, usage.output_tokens, cache_read),
        )
