"""Log bang structlog: console tieng Viet khi dev, JSON ra file khi chay that."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import Any

import structlog

from agent_cskh.config import Settings

_TOKEN_KEYS = {"token", "api_key", "secret", "authorization", "webhook_secret"}


def _redact(_logger: Any, _name: str, event: dict[str, Any]) -> dict[str, Any]:
    """Chan bi mat lot vao log — chay trong moi tien trinh xu ly."""
    for k in list(event):
        if any(t in k.lower() for t in _TOKEN_KEYS):
            event[k] = "<redacted>"
    return event


def setup_logging(settings: Settings) -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # stdout cua Windows mac dinh khong phai UTF-8 — ep lai de tieng Viet khong loi.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    file_handler = logging.handlers.RotatingFileHandler(
        settings.log_dir / "agent.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(processor=structlog.processors.JSONRenderer())
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=not settings.log_json)
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console)
    root.setLevel(level)

    # Thu vien HTTP rat on — chi cho len tu WARNING.
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            _redact,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
