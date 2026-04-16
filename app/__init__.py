import logging
import logging.handlers
import os
import time
import traceback
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import ALLOWED_ORIGINS, DOCS, XRAY_SUBSCRIPTION_PATH

__version__ = "0.8.4"

app = FastAPI(
    title="MarzbanAPI",
    description="Unified GUI Censorship Resistant Solution Powered by Xray",
    version=__version__,
    docs_url="/docs" if DOCS else None,
    redoc_url="/redoc" if DOCS else None,
)

scheduler = BackgroundScheduler(
    {"apscheduler.job_defaults.max_instances": 20}, timezone="UTC"
)
logger = logging.getLogger("uvicorn.error")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_exceptions_middleware(request: Request, call_next):
    """
    Логирует полный traceback любого необработанного исключения, которое
    вылетает из роутеров/зависимостей, ДО того как Starlette превратит
    его в 500 ответ. Нужен, чтобы в docker logs всегда появлялись
    подробности причины 500, а не только строка access-лога.

    HTTPException (в т.ч. 4xx/5xx намеренно брошенные роутерами) —
    это контракт API, их trace не пишем, чтобы не шуметь.
    Любой не-HTTP exception пробрасываем дальше неизменённым, чтобы
    поведение для клиента не поменялось.
    """
    started_at = time.monotonic()
    try:
        return await call_next(request)
    except (HTTPException, StarletteHTTPException):
        raise
    except Exception as exc:
        duration_ms = int((time.monotonic() - started_at) * 1000)
        client_host = request.client.host if request.client else "-"
        user_agent = request.headers.get("user-agent", "-")
        logger.error(
            "Unhandled exception in %s %s?%s from %s ua=%r after %dms: "
            "%s: %s\n%s",
            request.method,
            request.url.path,
            request.url.query or "",
            client_host,
            user_agent,
            duration_ms,
            type(exc).__name__,
            exc,
            traceback.format_exc(),
        )
        raise


from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics"],
    inprogress_name="http_requests_in_progress",
    inprogress_labels=True,
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

from app import dashboard, jobs, routers, telegram  # noqa
from app.routers import api_router  # noqa

app.include_router(api_router)


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


use_route_names_as_operation_ids(app)


def _setup_file_logging() -> None:
    """
    Вешает RotatingFileHandler на uvicorn-loggers так, чтобы access-лог
    и все traceback'и из log_exceptions_middleware писались на хостовой
    том, смонтированный в /var/log/app (см. docker-compose.yaml сервиса
    marzban). Это нужно, чтобы логи переживали recreate контейнера через
    refresh.sh (json-file driver их стирает при удалении container id).

    Вызывается из on_startup() — гарантированно ПОСЛЕ того как uvicorn
    сконфигурировал свои loggers через log_config dictConfig, иначе наш
    handler был бы затёрт.
    """
    log_dir = Path(os.getenv("LOG_DIR", "/var/log/app"))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning("Failed to create log dir %s: %s; file logging disabled", log_dir, e)
        return

    try:
        max_bytes = int(os.getenv("LOG_FILE_MAX_SIZE_MB", "50")) * 1024 * 1024
        backup_count = int(os.getenv("LOG_FILE_BACKUP_COUNT", "10"))
    except ValueError:
        max_bytes = 50 * 1024 * 1024
        backup_count = 10

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Один файл на оба канала — так проще искать трейсбеки рядом с access-логом.
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "marzban.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(fmt)

    # Маркер, чтобы не добавлять handler дважды при горячей перезагрузке воркера.
    handler._marzban_file_handler = True  # type: ignore[attr-defined]

    for logger_name in ("uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(logger_name)
        if any(getattr(h, "_marzban_file_handler", False) for h in lg.handlers):
            continue
        lg.addHandler(handler)

    logger.info(
        "File logging enabled: %s (max=%dMB, backups=%d)",
        log_dir / "marzban.log",
        max_bytes // (1024 * 1024),
        backup_count,
    )


@app.on_event("startup")
def on_startup():
    paths = [f"{r.path}/" for r in app.routes]
    paths.append("/api/")
    if f"/{XRAY_SUBSCRIPTION_PATH}/" in paths:
        raise ValueError(
            f"you can't use /{XRAY_SUBSCRIPTION_PATH}/ as subscription path it reserved for {app.title}"
        )
    _setup_file_logging()
    scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown()
    from app.utils.concurrency import shutdown_xray_executor
    shutdown_xray_executor(wait=True)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = {}
    for error in exc.errors():
        details[error["loc"][-1]] = error.get("msg")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": details}),
    )
