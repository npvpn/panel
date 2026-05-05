import os
import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import (
    SQLALCHEMY_DATABASE_URL,
    SQLALCHEMY_POOL_SIZE,
    SQLALCHEMY_POOL_TIMEOUT,
    SQLIALCHEMY_MAX_OVERFLOW,
)
from app import logger
from app.utils.request_context import snapshot

IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith('sqlite')

if IS_SQLITE:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=SQLALCHEMY_POOL_SIZE,
        max_overflow=SQLIALCHEMY_MAX_OVERFLOW,
        pool_recycle=3600,
        pool_timeout=SQLALCHEMY_POOL_TIMEOUT
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


_SLOW_SQL_MS = int(os.getenv("SLOW_SQL_MS", "200"))


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    try:
        conn.info["query_start_time"] = time.monotonic()
    except Exception:
        pass


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    try:
        started = conn.info.pop("query_start_time", None)
        if started is None:
            return
        dur_ms = int((time.monotonic() - started) * 1000)
        if dur_ms < _SLOW_SQL_MS:
            return

        ctx = snapshot()
        # avoid huge logs: single-line & truncate
        sql = " ".join(str(statement).split())
        if len(sql) > 500:
            sql = sql[:500] + "…"

        logger.warning(
            "[sql.slow] rid=%s method=%s handler=%s tmpl=%s dur_ms=%d sql=%r",
            ctx.request_id or "-",
            ctx.method or "-",
            ctx.handler or "-",
            ctx.path_template or "-",
            dur_ms,
            sql,
        )
    except Exception:
        # Never break the query path because of logging
        return


class Base(DeclarativeBase):
    pass
