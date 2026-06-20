from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass

_TEXT_FORMAT = (
    "%(asctime)s %(levelname)-8s %(name)s"
    " [rid=%(rid)s node=%(node_id)s user=%(user_id)s] %(message)s"
)


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LogSettings:
    level: str = "INFO"
    format: str = "text"
    dir: str = "/var/log/app"
    file_max_size_mb: int = 50
    file_backup_count: int = 10
    access_enabled: bool = True
    sql_slow_enabled: bool = True
    access_noise_paths: tuple[str, ...] = ("/metrics",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LogSettings:
        return cls(
            level=env.get("LOG_LEVEL", "INFO").upper(),
            format=env.get("LOG_FORMAT", "text").lower(),
            dir=env.get("LOG_DIR", "/var/log/app"),
            file_max_size_mb=int(env.get("LOG_FILE_MAX_SIZE_MB", "50")),
            file_backup_count=int(env.get("LOG_FILE_BACKUP_COUNT", "10")),
            access_enabled=_as_bool(env.get("LOG_ACCESS_ENABLED"), True),
            sql_slow_enabled=_as_bool(env.get("LOG_SQL_SLOW_ENABLED"), True),
            access_noise_paths=tuple(
                p.strip()
                for p in env.get("LOG_ACCESS_NOISE_PATHS", "/metrics").split(",")
                if p.strip()
            ),
        )


def build_logging_config(settings: LogSettings) -> dict:
    formatter = (
        {"()": "app.logging_config.JsonFormatter"}
        if settings.format == "json"
        else {"format": _TEXT_FORMAT}
    )
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context": {"()": "app.logging_context.ContextFilter"},
            "access_noise": {
                "()": "app.logging_context.AccessNoiseFilter",
                "noise_paths": list(settings.access_noise_paths),
            },
        },
        "formatters": {"default": formatter},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["context"],
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filters": ["context"],
                "filename": f"{settings.dir}/marzban.log",
                "maxBytes": settings.file_max_size_mb * 1024 * 1024,
                "backupCount": settings.file_backup_count,
                "encoding": "utf-8",
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["context", "access_noise"],
            },
        },
        "loggers": {
            "uvicorn.error": {
                "handlers": ["console", "file"],
                "level": settings.level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO" if settings.access_enabled else "CRITICAL",
                "propagate": False,
            },
            "app": {
                "handlers": ["console", "file"],
                "level": settings.level,
                "propagate": False,
            },
        },
        "root": {"handlers": ["console", "file"], "level": settings.level},
    }


class JsonFormatter:
    """Минимальный JSON-форматтер (для LOG_FORMAT=json)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": getattr(record, "asctime", None),
            "level": record.levelname,
            "logger": record.name,
            "rid": getattr(record, "rid", "-"),
            "node_id": getattr(record, "node_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "msg": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)
