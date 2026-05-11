from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from uuid import uuid4


_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace_id_var.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(TraceIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] [%(trace_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name)


def new_trace_id() -> str:
    return uuid4().hex


def set_trace_id(trace_id: str | None = None) -> Token[str]:
    return _trace_id_var.set(trace_id or new_trace_id())


def get_trace_id() -> str:
    return _trace_id_var.get()


def reset_trace_id(token: Token[str]) -> None:
    _trace_id_var.reset(token)
