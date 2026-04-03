from functools import lru_cache
import threading
import time
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app import logger, xray
from app.db import GetDB, crud
from app.models.node import NodeStatus
from app.models.user import UserResponse
from app.utils.concurrency import threaded_function
from app.xray.node import XRayNode
from config import (
    XRAY_NODE_CONNECT_RETRIES,
    XRAY_NODE_CONNECT_RETRY_DELAY,
    XRAY_NODE_CONNECT_STALE_TIMEOUT,
)
from xray_api import XRay as XRayAPI
from xray_api.types.account import Account, XTLSFlows

if TYPE_CHECKING:
    from app.db import User as DBUser
    from app.db.models import Node as DBNode


@lru_cache(maxsize=None)
def get_tls():
    from app.db import GetDB, get_tls_certificate
    with GetDB() as db:
        tls = get_tls_certificate(db)
        return {
            "key": tls.key,
            "certificate": tls.certificate
        }


@threaded_function
def _add_user_to_inbound(api: XRayAPI, inbound_tag: str, account: Account):
    try:
        api.add_inbound_user(tag=inbound_tag, user=account, timeout=60)
    except xray.exc.EmailNotFoundError as e:
        # User may be absent on this inbound/node; removal is idempotent.
        logger.debug(f"[xray.add_user.call][error] inbound={inbound_tag} email={getattr(account, 'email', 'unknown')} error={type(e).__name__}: {e}")
    except (xray.exc.ConnectionError, xray.exc.TimeoutError) as e:
        logger.warning(f"[xray.add_user.call][error] inbound={inbound_tag} email={getattr(account, 'email', 'unknown')} error={type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"[xray.add_user.call][unexpected] inbound={inbound_tag} email={getattr(account, 'email', 'unknown')} error={type(e).__name__}: {e}")


@threaded_function
def _remove_user_from_inbound(api: XRayAPI, inbound_tag: str, email: str):
    try:
        api.remove_inbound_user(tag=inbound_tag, email=email, timeout=10)
    except xray.exc.EmailNotFoundError as e:
        # User may be absent on this inbound/node; removal is idempotent.
        logger.debug(f"[xray.remove_user.call][error] inbound={inbound_tag} email={email} error={type(e).__name__}: {e}")
    except (xray.exc.ConnectionError, xray.exc.TimeoutError) as e:
        logger.warning(f"[xray.remove_user.call][error] inbound={inbound_tag} email={email} error={type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"[xray.remove_user.call][unexpected] inbound={inbound_tag} email={email} error={type(e).__name__}: {e}")


@threaded_function
def _alter_inbound_user(api: XRayAPI, inbound_tag: str, account: Account):
    try:
        api.remove_inbound_user(tag=inbound_tag, email=account.email, timeout=60)
    except xray.exc.EmailNotFoundError as e:
        # User may be absent on this inbound/node; removal is idempotent.
        logger.debug(f"[xray.alter_user.call][skip] step=remove inbound={inbound_tag} email={account.email} error={type(e).__name__}: {e}")
    except (xray.exc.ConnectionError, xray.exc.TimeoutError) as e:
        logger.warning(f"[xray.alter_user.call][error] step=remove inbound={inbound_tag} email={account.email} error={type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"[xray.alter_user.call][unexpected] step=remove inbound={inbound_tag} email={account.email} error={type(e).__name__}: {e}")
    try:
        api.add_inbound_user(tag=inbound_tag, user=account, timeout=60)
    except (xray.exc.EmailExistsError, xray.exc.ConnectionError, xray.exc.TimeoutError) as e:
        logger.warning(f"[xray.alter_user.call][error] step=add inbound={inbound_tag} email={account.email} error={type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"[xray.alter_user.call][unexpected] step=add inbound={inbound_tag} email={account.email} error={type(e).__name__}: {e}")


def add_user(dbuser: "DBUser"):
    user = UserResponse.model_validate(dbuser)
    email = f"{dbuser.id}.{dbuser.username}"

    for proxy_type, inbound_tags in user.inbounds.items():
        for inbound_tag in inbound_tags:
            inbound = xray.config.inbounds_by_tag.get(inbound_tag, {})

            try:
                proxy_settings = user.proxies[proxy_type].dict(no_obj=True)
            except KeyError:
                pass
            account = proxy_type.account_model(email=email, **proxy_settings)

            # XTLS currently only supports transmission methods of TCP and mKCP
            if getattr(account, 'flow', None) and (
                inbound.get('network', 'tcp') not in ('tcp', 'kcp')
                or
                (
                    inbound.get('network', 'tcp') in ('tcp', 'kcp')
                    and
                    inbound.get('tls') not in ('tls', 'reality')
                )
                or
                inbound.get('header_type') == 'http'
            ):
                account.flow = XTLSFlows.NONE

            _add_user_to_inbound(xray.api, inbound_tag, account)  # main core
            for node in list(xray.nodes.values()):
                # Не допускаем падения при недоступной ноде
                try:
                    if node.connected and node.started:
                        _add_user_to_inbound(node.api, inbound_tag, account)
                except Exception as e:
                    logger.warning(f"XRAY node check/add failed for user \"{dbuser.username}\" on inbound \"{inbound_tag}\": {e}")


def remove_user(dbuser: "DBUser"):
    email = f"{dbuser.id}.{dbuser.username}"
    user = UserResponse.model_validate(dbuser)

    # Build set of factual inbounds for this user (actual protocol tags assigned)
    target_inbounds = set()
    try:
        for _, inbound_tags in user.inbounds.items():
            for inbound_tag in inbound_tags:
                target_inbounds.add(inbound_tag)
    except Exception:
        target_inbounds = set()

    # Fallback: if we could not determine factual inbounds, fallback to all configured
    if not target_inbounds:
        target_inbounds = set(xray.config.inbounds_by_tag.keys())

    try:
        total_inbounds = len(xray.config.inbounds_by_tag)
    except Exception:
        total_inbounds = 0
    try:
        total_nodes = len(xray.nodes)
    except Exception:
        total_nodes = 0
    logger.info(f"[xray.remove_user] start email={email} target_inbounds={len(target_inbounds)} total_inbounds={total_inbounds} nodes={total_nodes}")

    # Precompute ready nodes once to avoid per-inbound status checks (expensive network calls)
    nodes_list = list(xray.nodes.values())
    ready_nodes = []
    _nodes_check_t0 = time.time()
    for node in nodes_list:
        # Avoid network calls in properties; rely on cached flags where possible
        is_started_cached = False
        has_session = True
        try:
            # ReSTXRayNode uses _started and _session_id
            if hasattr(node, "_started"):
                is_started_cached = bool(getattr(node, "_started"))
                has_session = bool(getattr(node, "_session_id", None))
            # RPyCXRayNode uses 'started'
            elif hasattr(node, "started"):
                is_started_cached = bool(getattr(node, "started"))
            else:
                is_started_cached = False
        except Exception:
            is_started_cached = False
        if is_started_cached and has_session:
            ready_nodes.append(node)
    logger.info(f"[xray.remove_user] nodes_ready={len(ready_nodes)} nodes_checked={len(nodes_list)}")

    for inbound_tag in target_inbounds:
        _remove_user_from_inbound(xray.api, inbound_tag, email)
        for node in ready_nodes:
            # Не допускаем падения при недоступной ноде
            try:
                _remove_user_from_inbound(node.api, inbound_tag, email)
            except Exception as e:
                logger.warning(f"XRAY node check/remove failed for user \"{dbuser.username}\" on inbound \"{inbound_tag}\": {type(e).__name__}: {e}")


def update_user(dbuser: "DBUser"):
    user = UserResponse.model_validate(dbuser)
    email = f"{dbuser.id}.{dbuser.username}"

    active_inbounds = []
    for proxy_type, inbound_tags in user.inbounds.items():
        for inbound_tag in inbound_tags:
            active_inbounds.append(inbound_tag)
            inbound = xray.config.inbounds_by_tag.get(inbound_tag, {})

            try:
                proxy_settings = user.proxies[proxy_type].dict(no_obj=True)
            except KeyError:
                pass
            account = proxy_type.account_model(email=email, **proxy_settings)

            # XTLS currently only supports transmission methods of TCP and mKCP
            if getattr(account, 'flow', None) and (
                inbound.get('network', 'tcp') not in ('tcp', 'kcp')
                or
                (
                    inbound.get('network', 'tcp') in ('tcp', 'kcp')
                    and
                    inbound.get('tls') not in ('tls', 'reality')
                )
                or
                inbound.get('header_type') == 'http'
            ):
                account.flow = XTLSFlows.NONE

            _alter_inbound_user(xray.api, inbound_tag, account)  # main core
            for node in list(xray.nodes.values()):
                # Не допускаем падения при недоступной ноде
                try:
                    if node.connected and node.started:
                        _alter_inbound_user(node.api, inbound_tag, account)
                except Exception as e:
                    logger.warning(f"XRAY node check/alter failed for user \"{dbuser.username}\" on inbound \"{inbound_tag}\": {e}")

    for inbound_tag in xray.config.inbounds_by_tag:
        if inbound_tag in active_inbounds:
            continue
        # remove disabled inbounds
        _remove_user_from_inbound(xray.api, inbound_tag, email)
        for node in list(xray.nodes.values()):
            # Не допускаем падения при недоступной ноде
            try:
                if node.connected and node.started:
                    _remove_user_from_inbound(node.api, inbound_tag, email)
            except Exception as e:
                logger.warning(f"XRAY node check/remove (disabled inbound) failed for user \"{dbuser.username}\" on inbound \"{inbound_tag}\": {e}")


def update_user_by_id(user_id: int):
    """
    Safe wrapper to update a user in background tasks by reloading a fresh DB-bound instance.
    Prevents DetachedInstanceError when original dbuser is out of session.
    """
    with GetDB() as db:
        try:
            dbuser = crud.get_user_by_id(db, user_id)
            if not dbuser:
                return
            update_user(dbuser)
        except SQLAlchemyError:
            db.rollback()
            raise


def remove_node(node_id: int):
    if node_id in xray.nodes:
        try:
            xray.nodes[node_id].disconnect()
        except Exception:
            pass
        finally:
            try:
                del xray.nodes[node_id]
            except KeyError:
                pass


def add_node(dbnode: "DBNode"):
    remove_node(dbnode.id)

    tls = get_tls()
    xray.nodes[dbnode.id] = XRayNode(address=dbnode.address,
                                     port=dbnode.port,
                                     api_port=dbnode.api_port,
                                     ssl_key=tls['key'],
                                     ssl_cert=tls['certificate'],
                                     usage_coefficient=dbnode.usage_coefficient)

    return xray.nodes[dbnode.id]


def _change_node_status(node_id: int, status: NodeStatus, message: str = None, version: str = None) -> bool:
    with GetDB() as db:
        try:
            dbnode = crud.get_node_by_id(db, node_id)
            if not dbnode:
                logger.warning(f"[node.status] node_id={node_id} not found for status={status.value}")
                return False

            if dbnode.status == NodeStatus.disabled:
                remove_node(dbnode.id)
                logger.info(f"[node.status] node_id={node_id} is disabled; status update skipped")
                return False

            crud.update_node_status(db, dbnode, status, message, version)
            return True
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(
                f"[node.status] failed to update node_id={node_id} status={status.value}: {type(exc).__name__}: {exc}"
            )
            raise


global _connecting_nodes
_connecting_nodes = set()
_connecting_started_at = {}
_connecting_nodes_lock = threading.Lock()


def _acquire_connect_slot(node_id: int, force: bool = False) -> bool:
    now = time.time()
    with _connecting_nodes_lock:
        if node_id in _connecting_nodes:
            started_at = _connecting_started_at.get(node_id, now)
            age = now - started_at

            if force and age >= XRAY_NODE_CONNECT_STALE_TIMEOUT:
                logger.warning(
                    f"[connect_node] force-acquire for stale lock, node_id={node_id}, age={age:.1f}s"
                )
                _connecting_nodes.discard(node_id)
                _connecting_started_at.pop(node_id, None)
            else:
                logger.debug(
                    f"[connect_node] skipped, already connecting node_id={node_id}, age={age:.1f}s"
                )
                return False

        _connecting_nodes.add(node_id)
        _connecting_started_at[node_id] = now
        return True


def _release_connect_slot(node_id: int):
    with _connecting_nodes_lock:
        _connecting_nodes.discard(node_id)
        _connecting_started_at.pop(node_id, None)


@threaded_function
def connect_node(node_id, config=None, force: bool = False):
    if not _acquire_connect_slot(node_id, force=force):
        return

    dbnode = None
    node = None

    try:
        with GetDB() as db:
            dbnode = crud.get_node_by_id(db, node_id)

        if not dbnode:
            return

        if dbnode.status == NodeStatus.disabled:
            remove_node(dbnode.id)
            logger.info(f"[connect_node] skip disabled node_id={dbnode.id}")
            return

        status_changed = _change_node_status(node_id, NodeStatus.connecting)
        if not status_changed:
            logger.info(f"[connect_node] status update rejected for node_id={node_id}")
            return

        if config is None:
            config = xray.config.include_db_users()
        retries = max(1, XRAY_NODE_CONNECT_RETRIES)
        retry_delay = max(0, XRAY_NODE_CONNECT_RETRY_DELAY)
        last_exc = None
        try:
            node = xray.nodes[dbnode.id]
        except KeyError:
            node = xray.operations.add_node(dbnode)

        for attempt in range(1, retries + 1):
            try:
                logger.info(
                    f"Connecting to \"{dbnode.name}\" node (attempt {attempt}/{retries})"
                )
                node.start(config)
                version = node.get_version()
                _change_node_status(node_id, NodeStatus.connected, version=version)
                logger.info(f"Connected to \"{dbnode.name}\" node, xray run on v{version}")
                return
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    delay = retry_delay * attempt
                    logger.warning(
                        f"[connect_node] attempt {attempt}/{retries} failed for "
                        f"node_id={node_id} ({dbnode.name}): {type(exc).__name__}: {exc}. "
                        f"retry in {delay}s"
                    )
                    if delay:
                        time.sleep(delay)
                    continue
                raise last_exc

    except Exception as exc:
        try:
            _change_node_status(node_id, NodeStatus.error, message=str(exc))
        except Exception as status_exc:
            logger.error(
                f"[connect_node] failed to mark node_id={node_id} as error: "
                f"{type(status_exc).__name__}: {status_exc}"
            )
        if dbnode:
            logger.warning(f"Unable to connect to \"{dbnode.name}\" node: {type(exc).__name__}: {exc}")
        else:
            logger.warning(f"Unable to connect node_id={node_id}: {type(exc).__name__}: {exc}")
    finally:
        _release_connect_slot(node_id)
        if dbnode:
            try:
                logger.debug(f"[connect_node] released lock for node_id={node_id} ({dbnode.name})")
            except Exception:
                logger.debug(f"[connect_node] released lock for node_id={node_id}")
        else:
            logger.debug(f"[connect_node] released lock for node_id={node_id}")


@threaded_function
def restart_node(node_id, config=None):
    with GetDB() as db:
        dbnode = crud.get_node_by_id(db, node_id)

    if not dbnode:
        return

    try:
        node = xray.nodes[dbnode.id]
    except KeyError:
        node = xray.operations.add_node(dbnode)

    if not node.connected:
        return connect_node(node_id, config)

    try:
        logger.info(f"Restarting Xray core of \"{dbnode.name}\" node")

        if config is None:
            config = xray.config.include_db_users()

        node.restart(config)
        logger.info(f"Xray core of \"{dbnode.name}\" node restarted")
    except Exception as e:
        try:
            _change_node_status(node_id, NodeStatus.error, message=str(e))
        except Exception as status_exc:
            logger.error(
                f"[restart_node] failed to mark node_id={node_id} as error: "
                f"{type(status_exc).__name__}: {status_exc}"
            )
        logger.info(f"Unable to restart node {node_id}")
        try:
            node.disconnect()
        except Exception:
            pass


__all__ = [
    "add_user",
    "remove_user",
    "update_user_by_id",
    "add_node",
    "remove_node",
    "connect_node",
    "restart_node",
]
