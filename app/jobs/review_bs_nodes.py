"""Reconcile по-нодных лимитов БС-нод (NPVPN-1456).

Сравнивает node_user_bs_usage с лимитами БС-нод, ведёт node_user_blocks и
снимает/возвращает пользователя на конкретной ноде. Тяжёлую node_user_usages
не трогает; desired-blocked считается отфильтрованным запросом (только нарушители).
"""
import time
from datetime import datetime

from sqlalchemy import and_, case, or_

from app import logger, scheduler, xray
from app.db import GetDB
from app.db.crud import get_user_by_id
from app.db.models import Node, NodeUserBlock, NodeUserBsUsage
from app.models.user import UserStatus
from app.xray.bs_limit import diff_blocks, period_keys
from config import JOB_REVIEW_BS_NODES_INTERVAL


def review_bs_nodes():
    t0 = time.monotonic()
    today, yyyymm = period_keys(datetime.utcnow())

    with GetDB() as db:
        # desired-blocked: только превысившие, период не устарел. period — диагностика.
        period_expr = case(
            (and_(Node.bs_daily_limit.isnot(None),
                  NodeUserBsUsage.daily_period == today,
                  NodeUserBsUsage.daily_used >= Node.bs_daily_limit), "day"),
            else_="month",
        )
        rows = db.query(
            NodeUserBsUsage.node_id,
            NodeUserBsUsage.user_id,
            period_expr.label("period"),
        ).join(
            Node, Node.id == NodeUserBsUsage.node_id
        ).filter(
            Node.is_bs.is_(True),
            or_(
                and_(Node.bs_daily_limit.isnot(None),
                     NodeUserBsUsage.daily_period == today,
                     NodeUserBsUsage.daily_used >= Node.bs_daily_limit),
                and_(Node.bs_monthly_limit.isnot(None),
                     NodeUserBsUsage.monthly_period == yyyymm,
                     NodeUserBsUsage.monthly_used >= Node.bs_monthly_limit),
            ),
        ).all()

        desired = {(r.node_id, r.user_id) for r in rows}
        desired_period = {(r.node_id, r.user_id): r.period for r in rows}

        current_rows = db.query(NodeUserBlock.id, NodeUserBlock.node_id,
                                NodeUserBlock.user_id).all()
        current = {(r.node_id, r.user_id) for r in current_rows}
        block_id = {(r.node_id, r.user_id): r.id for r in current_rows}

        to_block, to_unblock = diff_blocks(desired, current)

        for node_id, user_id in to_block:
            dbuser = get_user_by_id(db, user_id)
            if not dbuser:
                continue
            db.add(NodeUserBlock(
                node_id=node_id, user_id=user_id,
                period=desired_period.get((node_id, user_id), "day"),
                created_at=datetime.utcnow(),
            ))
            db.commit()
            try:
                xray.operations.remove_user_from_node(dbuser, node_id)
            except Exception as e:
                logger.warning(f"[review_bs_nodes] remove failed node={node_id} "
                               f"user_id={user_id}: {type(e).__name__}: {e}")
            logger.info(f"[review_bs_nodes] blocked user_id={user_id} on node_id={node_id} "
                        f"({desired_period.get((node_id, user_id))})")

        for node_id, user_id in to_unblock:
            # Строку блокировки удаляем безусловно (лимит больше не превышен).
            # add_user_to_node ниже — только для активных юзеров; неактивных
            # (limited/expired) на ноду не возвращаем, их вернёт штатный flow при
            # смене статуса. Поэтому удаление блока развязано с реальным re-add.
            bid = block_id.get((node_id, user_id))
            if bid is not None:
                db.query(NodeUserBlock).filter(NodeUserBlock.id == bid).delete()
                db.commit()
            dbuser = get_user_by_id(db, user_id)
            if dbuser and dbuser.status in (UserStatus.active, UserStatus.on_hold):
                try:
                    xray.operations.add_user_to_node(dbuser, node_id)
                except Exception as e:
                    logger.warning(f"[review_bs_nodes] add failed node={node_id} "
                                   f"user_id={user_id}: {type(e).__name__}: {e}")
            logger.info(f"[review_bs_nodes] unblocked user_id={user_id} on node_id={node_id}")

    if to_block or to_unblock:
        logger.info(f"[review_bs_nodes] done blocked={len(to_block)} unblocked={len(to_unblock)} "
                    f"dt={time.monotonic() - t0:.2f}s")


scheduler.add_job(review_bs_nodes, 'interval',
                  seconds=JOB_REVIEW_BS_NODES_INTERVAL,
                  coalesce=True, max_instances=1)
