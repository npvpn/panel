"""Reconcile агрегатного per-bot лимита БС-нод (NPVPN-1456).

Суммирует node_user_bs_usage по всем is_bs-нодам юзера за текущий период,
сравнивает с per-bot лимитом из BotSettings.data и при превышении блокирует
юзера на ВСЕХ БС-нодах (node_user_blocks). Тяжёлую node_user_usages не трогает.
"""

import time
from datetime import datetime

from app import logger, scheduler, xray
from app.db import GetDB
from app.db.crud import get_user_by_id
from app.db.models import BotSettings, Node, NodeUserBlock, NodeUserBsUsage, User
from app.models.bot import apply_bot_settings_fallback
from app.models.user import UserStatus
from app.xray.bs_limit import aggregate_bs_usage, diff_blocks, over_limit, period_keys
from config import JOB_REVIEW_BS_NODES_INTERVAL


def _bot_limits(db):
    """{bot_id: (daily_limit, monthly_limit)} в байтах из BotSettings.data."""
    limits = {}
    for bot_id, data in db.query(BotSettings.bot_id, BotSettings.data).all():
        settings = apply_bot_settings_fallback(data)
        limits[bot_id] = (settings.get("bs_daily_limit") or 0, settings.get("bs_monthly_limit") or 0)
    return limits


def review_bs_nodes():
    t0 = time.monotonic()
    today, yyyymm = period_keys(datetime.utcnow())
    to_block, to_unblock = set(), set()

    with GetDB() as db:
        bs_node_ids = {nid for (nid,) in db.query(Node.id).filter(Node.is_bs.is_(True)).all()}
        if not bs_node_ids:
            return

        usage_rows = (
            db.query(
                NodeUserBsUsage.user_id,
                NodeUserBsUsage.daily_used,
                NodeUserBsUsage.daily_period,
                NodeUserBsUsage.monthly_used,
                NodeUserBsUsage.monthly_period,
            )
            .filter(NodeUserBsUsage.node_id.in_(bs_node_ids))
            .all()
        )

        totals = aggregate_bs_usage(
            [
                {
                    "user_id": r.user_id,
                    "daily_used": r.daily_used,
                    "daily_period": r.daily_period,
                    "monthly_used": r.monthly_used,
                    "monthly_period": r.monthly_period,
                }
                for r in usage_rows
            ],
            today,
            yyyymm,
        )

        bot_limits = _bot_limits(db)
        user_ids = list(totals.keys())
        user_bot = dict(db.query(User.id, User.bot_id).filter(User.id.in_(user_ids)).all()) if user_ids else {}

        over_users = set()
        for uid, t in totals.items():
            dl, ml = bot_limits.get(user_bot.get(uid), (0, 0))
            if over_limit(t["daily_used"], t["monthly_used"], dl, ml):
                over_users.add(uid)

        desired = {(nid, uid) for uid in over_users for nid in bs_node_ids}

        current_rows = db.query(NodeUserBlock.id, NodeUserBlock.node_id, NodeUserBlock.user_id).all()
        current = {(r.node_id, r.user_id) for r in current_rows}
        block_id = {(r.node_id, r.user_id): r.id for r in current_rows}

        to_block, to_unblock = diff_blocks(desired, current)

        for node_id, user_id in to_block:
            dbuser = get_user_by_id(db, user_id)
            if not dbuser:
                continue
            db.add(NodeUserBlock(node_id=node_id, user_id=user_id, period="agg", created_at=datetime.utcnow()))
            db.commit()
            try:
                xray.operations.remove_user_from_node(dbuser, node_id)
            except Exception as e:
                logger.warning(
                    f"[review_bs_nodes] remove failed node={node_id} user_id={user_id}: {type(e).__name__}: {e}"
                )
            logger.info(f"[review_bs_nodes] blocked user_id={user_id} on node_id={node_id}")

        for node_id, user_id in to_unblock:
            bid = block_id.get((node_id, user_id))
            if bid is not None:
                db.query(NodeUserBlock).filter(NodeUserBlock.id == bid).delete()
                db.commit()
            dbuser = get_user_by_id(db, user_id)
            if dbuser and dbuser.status in (UserStatus.active, UserStatus.on_hold):
                try:
                    xray.operations.add_user_to_node(dbuser, node_id)
                except Exception as e:
                    logger.warning(
                        f"[review_bs_nodes] add failed node={node_id} user_id={user_id}: {type(e).__name__}: {e}"
                    )
            logger.info(f"[review_bs_nodes] unblocked user_id={user_id} on node_id={node_id}")

    if to_block or to_unblock:
        logger.info(
            f"[review_bs_nodes] done blocked={len(to_block)} unblocked={len(to_unblock)} "
            f"dt={time.monotonic() - t0:.2f}s"
        )


scheduler.add_job(review_bs_nodes, "interval", seconds=JOB_REVIEW_BS_NODES_INTERVAL, coalesce=True, max_instances=1)
