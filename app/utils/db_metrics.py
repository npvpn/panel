"""SQLAlchemy QueuePool exporter for Prometheus.

Exposes pool capacity/usage as gauges and counts slow/timed-out checkouts. Lets
Grafana surface the symptom we hit in NPVPN-1170: pool fully used while MySQL
itself was idle (real bottleneck was the starlette threadpool, but the pool
metric is what visually screams first).
"""
from prometheus_client import REGISTRY, Counter
from prometheus_client.core import GaugeMetricFamily

from app import logger

db_checkout_slow_total = Counter(
    "db_checkout_slow_total",
    "Number of DB session checkouts that waited longer than SLOW_SQL_MS",
)
db_checkout_timeout_total = Counter(
    "db_checkout_timeout_total",
    "Number of DB session checkouts that exceeded SQLALCHEMY_POOL_TIMEOUT",
)


class _DbPoolCollector:
    """Reads engine.pool stats at each /metrics scrape — no background work."""

    def collect(self):
        try:
            from app.db.base import engine
        except Exception:
            return
        pool = getattr(engine, "pool", None)
        if pool is None:
            return

        size = _safe_call(pool, "size")
        checked_out = _safe_call(pool, "checkedout")
        overflow = _safe_call(pool, "overflow")
        checked_in = _safe_call(pool, "checkedin")
        max_overflow = getattr(pool, "_max_overflow", None)

        if size is not None:
            yield GaugeMetricFamily("db_pool_size", "Configured pool_size", value=size)
        if max_overflow is not None:
            yield GaugeMetricFamily(
                "db_pool_max_overflow", "Configured max_overflow", value=max_overflow
            )
        if checked_out is not None:
            yield GaugeMetricFamily("db_pool_checkedout", "Connections currently in use", value=checked_out)
        if overflow is not None:
            yield GaugeMetricFamily(
                "db_pool_overflow",
                "Connections beyond pool_size (negative if not all spawned yet)",
                value=overflow,
            )
        if checked_in is not None:
            yield GaugeMetricFamily("db_pool_checkedin", "Idle connections in the pool", value=checked_in)


def _safe_call(pool, name):
    fn = getattr(pool, name, None)
    if fn is None:
        return None
    try:
        return fn()
    except Exception:
        return None


_registered = False


def register():
    global _registered
    if _registered:
        return
    try:
        REGISTRY.register(_DbPoolCollector())
        _registered = True
    except Exception as exc:
        logger.warning("[metrics] failed to register db pool collector: %s", exc)
