import logging

from app.logging_context import (
    AccessNoiseFilter,
    ContextFilter,
    clear_log_context,
    set_log_context,
)


def _record(name: str = "t", msg: str = "msg") -> logging.LogRecord:
    return logging.LogRecord(name, logging.INFO, __file__, 1, msg, None, None)


def test_filter_injects_defaults_when_no_context():
    clear_log_context()
    rec = _record()
    assert ContextFilter().filter(rec) is True
    assert rec.rid == "-"
    assert rec.node_id == "-"
    assert rec.user_id == "-"


def test_filter_injects_set_context():
    set_log_context(rid="abc", node_id=7, user_id=42)
    rec = _record()
    ContextFilter().filter(rec)
    assert rec.rid == "abc"
    assert rec.node_id == "7"
    assert rec.user_id == "42"
    clear_log_context()


def test_access_noise_drops_metrics():
    f = AccessNoiseFilter(noise_paths=["/metrics"])
    assert f.filter(_record("uvicorn.access", "GET /metrics HTTP/1.1 200")) is False


def test_access_noise_keeps_errors_and_other_paths():
    f = AccessNoiseFilter(noise_paths=["/metrics"])
    assert f.filter(_record("uvicorn.access", "GET /api/admin HTTP/1.1 200")) is True
    assert f.filter(_record("uvicorn.access", "GET /metrics HTTP/1.1 500")) is True
