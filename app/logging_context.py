from __future__ import annotations

import logging
from contextvars import ContextVar

_rid: ContextVar[str | None] = ContextVar("log_rid", default=None)
_node_id: ContextVar[str | None] = ContextVar("log_node_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("log_user_id", default=None)


def set_log_context(*, rid: object = None, node_id: object = None, user_id: object = None) -> None:
    if rid is not None:
        _rid.set(str(rid))
    if node_id is not None:
        _node_id.set(str(node_id))
    if user_id is not None:
        _user_id.set(str(user_id))


def clear_log_context() -> None:
    _rid.set(None)
    _node_id.set(None)
    _user_id.set(None)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.rid = _rid.get() or "-"  # type: ignore[attr-defined]
        record.node_id = _node_id.get() or "-"  # type: ignore[attr-defined]
        record.user_id = _user_id.get() or "-"  # type: ignore[attr-defined]
        return True


class AccessNoiseFilter(logging.Filter):
    def __init__(self, noise_paths: list[str] | None = None) -> None:
        super().__init__()
        self._paths = noise_paths if noise_paths is not None else ["/metrics"]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        is_error = any(code in message for code in (" 4", " 5"))
        if is_error:
            return True
        return not any(path in message for path in self._paths)
