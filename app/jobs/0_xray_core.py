import time
import traceback

from app import app, logger, scheduler, xray
from app.db import GetDB, crud
from app.models.node import NodeStatus
from config import JOB_CORE_HEALTH_CHECK_INTERVAL
from app.xray.node import NodeAPIError
from xray_api import exc as xray_exc

_error_reconnect_last: dict[int, float] = {}


def _quick_node_ready(node) -> bool:
    """Cached readiness check — no network I/O."""
    try:
        if hasattr(node, "_session_id"):
            return bool(getattr(node, "_session_id", None)) and bool(getattr(node, "_started", False))
        if hasattr(node, "started"):
            return bool(getattr(node, "started", False))
    except Exception:
        pass
    return False


def _should_force_reconnect(node_id: int, status: NodeStatus, now: float) -> bool:
    if status == NodeStatus.connecting and xray.operations.is_connect_stale(node_id):
        return True
    if status != NodeStatus.error:
        return False
    last_attempt = _error_reconnect_last.get(node_id, 0)
    if now - last_attempt >= XRAY_NODE_ERROR_RECONNECT_INTERVAL:
        _error_reconnect_last[node_id] = now
        return True
    return False


def _quick_node_ready(node) -> bool:
    try:
        if hasattr(node, "_session_id"):
            return bool(getattr(node, "_session_id", None)) and bool(getattr(node, "_started", False))
        if hasattr(node, "started"):
            return bool(getattr(node, "started", False))
    except Exception:
        pass
    return False


def core_health_check():
    config = None
    now = time.time()

    # main core
    if not xray.core.started:
        if not config:
            config = xray.config.include_db_users()
        xray.core.restart(config)

    with GetDB() as db:
        dbnodes = crud.get_nodes(db=db, enabled=True)
        db_status = {dbnode.id: dbnode.status for dbnode in dbnodes}

    for node_id, node in list(xray.nodes.items()):
        status = db_status.get(node_id)

        # DB says error/connecting but in-memory session may look fine — reconnect anyway.
        if status in (NodeStatus.error, NodeStatus.connecting):
            if not config:
                config = xray.config.include_db_users()
            xray.operations.connect_node(node_id, config)
            continue

        if status == NodeStatus.connected and _quick_node_ready(node):
            try:
                node.api.get_sys_stats(timeout=2)
            except (ConnectionError, NodeAPIError, xray_exc.XrayError):
                if not config:
                    config = xray.config.include_db_users()
                xray.operations.connect_node(node_id, config)
            continue

        if not config:
            config = xray.config.include_db_users()
        xray.operations.connect_node(node_id, config)


@app.on_event("startup")
def start_core():
    logger.info("Generating Xray core config")

    start_time = time.time()
    config = xray.config.include_db_users()
    logger.info(f"Xray core config generated in {(time.time() - start_time):.2f} seconds")

    # main core
    logger.info("Starting main Xray core")
    try:
        xray.core.start(config)
    except Exception:
        traceback.print_exc()

    # nodes' core
    logger.info("Starting nodes Xray core")
    with GetDB() as db:
        dbnodes = crud.get_nodes(db=db, enabled=True)
        node_ids = [dbnode.id for dbnode in dbnodes]
        for dbnode in dbnodes:
            crud.update_node_status(db, dbnode, NodeStatus.connecting)

    for node_id in node_ids:
        xray.operations.connect_node(node_id, config)

    scheduler.add_job(core_health_check, 'interval',
                      seconds=JOB_CORE_HEALTH_CHECK_INTERVAL,
                      coalesce=True, max_instances=1)


@app.on_event("shutdown")
def app_shutdown():
    logger.info("Stopping main Xray core")
    xray.core.stop()

    logger.info("Stopping nodes Xray core")
    for node in list(xray.nodes.values()):
        try:
            node.disconnect()
        except Exception:
            pass
