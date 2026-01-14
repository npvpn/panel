from datetime import datetime
import time
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app import logger, scheduler, xray
from app.db import (GetDB, get_notification_reminder, get_users,
                    start_user_expire, update_user_status, reset_user_by_next)
from app.models.user import ReminderType, UserResponse, UserStatus
from app.utils import report
from app.utils.helpers import (calculate_expiration_days,
                               calculate_usage_percent)
from config import (JOB_REVIEW_USERS_INTERVAL, NOTIFY_DAYS_LEFT,
                    NOTIFY_REACHED_USAGE_PERCENT, WEBHOOK_ADDRESS)

if TYPE_CHECKING:
    from app.db.models import User


def add_notification_reminders(db: Session, user: "User", now: datetime = datetime.utcnow()) -> None:
    if user.data_limit:
        usage_percent = calculate_usage_percent(user.used_traffic, user.data_limit)

        for percent in sorted(NOTIFY_REACHED_USAGE_PERCENT, reverse=True):
            if usage_percent >= percent:
                if not get_notification_reminder(db, user.id, ReminderType.data_usage, threshold=percent):
                    report.data_usage_percent_reached(
                        db, usage_percent, UserResponse.model_validate(user),
                        user.id, user.expire, threshold=percent
                    )
                break

    if user.expire:
        expire_days = calculate_expiration_days(user.expire)

        for days_left in sorted(NOTIFY_DAYS_LEFT):
            if expire_days <= days_left:
                if not get_notification_reminder(db, user.id, ReminderType.expiration_date, threshold=days_left):
                    report.expire_days_reached(
                        db, expire_days, UserResponse.model_validate(user),
                        user.id, user.expire, threshold=days_left
                    )
                break


def reset_user_by_next_report(db: Session, user: "User"):
    user = reset_user_by_next(db, user, commit=False)

    # Даже если нода недоступна — не срываем джоб, просто логируем и продолжаем
    _t0 = time.time()
    try:
        xray.operations.update_user(user)
    except Exception as e:
        logger.warning(f"Failed to update user on XRAY during reset_user_by_next for \"{user.username}\": {e}")
    finally:
        _dur = time.time() - _t0
        logger.info(f"[review][next_plan] user=\"{user.username}\" xray_update_user took {_dur:.3f}s")

    report.user_data_reset_by_next(user=UserResponse.model_validate(user), user_admin=user.admin)


def review():
    now = datetime.utcnow()
    now_ts = now.timestamp()
    start_ts = time.time()
    SLOW_USER_TOTAL_THRESHOLD = 1.0
    SLOW_STEP_THRESHOLD = 0.3
    BATCH_SIZE_ACTIVE = 500
    BATCH_SIZE_ONHOLD = 500
    checked_active = 0
    applied_next = 0
    limited_count = 0
    expired_count = 0
    on_hold_activated = 0
    with GetDB() as db:
        _fetch_t0 = time.time()
        active_users = get_users(db, status=UserStatus.active)
        _fetch_dur = time.time() - _fetch_t0
        logger.info(f"[review] fetched {len(active_users)} active users in {_fetch_dur:.3f}s")

        # Process in deterministic order to reduce lock collisions
        try:
            active_users.sort(key=lambda u: u.id)
        except Exception:
            pass

        changed_in_batch = 0
        for user in active_users:
            checked_active += 1
            _u_t0 = time.time()
            _t_remove = 0.0
            _t_update_status = 0.0
            _t_notify = 0.0

            limited = user.data_limit and user.used_traffic >= user.data_limit
            expired = user.expire and user.expire <= now_ts

            if (limited or expired) and user.next_plan is not None:
                if user.next_plan is not None:

                    if user.next_plan.fire_on_either:
                        reset_user_by_next_report(db, user)
                        applied_next += 1
                        continue
                        
                    elif limited and expired:
                        reset_user_by_next_report(db, user)
                        applied_next += 1
                        continue

            if limited:
                status = UserStatus.limited
                limited_count += 1
            elif expired:
                status = UserStatus.expired
                expired_count += 1
            else:
                if WEBHOOK_ADDRESS:
                    _tn0 = time.time()
                    add_notification_reminders(db, user, now)
                    _t_notify = time.time() - _tn0
                continue

            # При недоступности XRAY-нод не допускаем падения задачи: статус все равно обновляем
            _tr0 = time.time()
            try:
                xray.operations.remove_user(user)
            except Exception as e:
                logger.warning(f"Failed to remove user \"{user.username}\" from XRAY: {e}")
            finally:
                _t_remove = time.time() - _tr0

            _ts0 = time.time()
            update_user_status(db, user, status, commit=False)
            _t_update_status = time.time() - _ts0

            report.status_change(username=user.username, status=status,
                                 user=UserResponse.model_validate(user), user_admin=user.admin)

            logger.info(f"User \"{user.username}\" status changed to {status}")
            _u_dur = time.time() - _u_t0
            changed_in_batch += 1

            # Commit batch periodically to avoid long-held locks
            if changed_in_batch >= BATCH_SIZE_ACTIVE:
                _commit_t0 = time.time()
                logger.warning(f"[review] starting commit for active batch size={changed_in_batch}")
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to commit active batch: {e}")
                    raise
                finally:
                    _commit_dur = time.time() - _commit_t0
                    logger.info(f"[review] commit of active batch took {_commit_dur:.3f}s")
                    changed_in_batch = 0

            if _u_dur >= SLOW_USER_TOTAL_THRESHOLD or _t_remove >= SLOW_STEP_THRESHOLD or _t_update_status >= SLOW_STEP_THRESHOLD or _t_notify >= SLOW_STEP_THRESHOLD:
                logger.info(
                    f"[review][active][slow] user=\"{user.username}\" total={_u_dur:.3f}s "
                    f"remove_user={_t_remove:.3f}s update_status={_t_update_status:.3f}s notify={_t_notify:.3f}s"
                )

        # Коммитим все изменения статусов/next-планов за один раз
        _commit_t0 = time.time()
        if changed_in_batch > 0:
            logger.warning(f"[review] starting final commit for remaining active size={changed_in_batch}")
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit batched review changes: {e}")
            raise
        finally:
            _commit_dur = time.time() - _commit_t0
            logger.info(f"[review] commit of active users took {_commit_dur:.3f}s")

        _fetch_hold_t0 = time.time()
        on_hold_users = get_users(db, status=UserStatus.on_hold)
        _fetch_hold_dur = time.time() - _fetch_hold_t0
        logger.info(f"[review] fetched {len(on_hold_users)} on_hold users in {_fetch_hold_dur:.3f}s")
        # Deterministic order
        try:
            on_hold_users.sort(key=lambda u: u.id)
        except Exception:
            pass
        changed_onhold_batch = 0
        for user in on_hold_users:
            _hold_u_t0 = time.time()
            _t_update_status_hold = 0.0
            _t_start_expire = 0.0

            if user.edit_at:
                base_time = datetime.timestamp(user.edit_at)
            else:
                base_time = datetime.timestamp(user.created_at)

            # Check if the user is online After or at 'base_time'
            if user.online_at and base_time <= datetime.timestamp(user.online_at):
                status = UserStatus.active

            elif user.on_hold_timeout and (datetime.timestamp(user.on_hold_timeout) <= (now_ts)):
                # If the user didn't connect within the timeout period, change status to "Active"
                status = UserStatus.active

            else:
                continue

            _ts0 = time.time()
            update_user_status(db, user, status, commit=False)
            _t_update_status_hold = time.time() - _ts0
            _te0 = time.time()
            start_user_expire(db, user, commit=False)
            _t_start_expire = time.time() - _te0
            on_hold_activated += 1
            changed_onhold_batch += 1

            if changed_onhold_batch >= BATCH_SIZE_ONHOLD:
                _commit_t0 = time.time()
                logger.warning(f"[review] starting commit for on_hold batch size={changed_onhold_batch}")
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to commit on_hold batch: {e}")
                    raise
                finally:
                    _commit_dur = time.time() - _commit_t0
                    logger.info(f"[review] commit of on_hold batch took {_commit_dur:.3f}s")
                    changed_onhold_batch = 0

            report.status_change(username=user.username, status=status,
                                 user=UserResponse.model_validate(user), user_admin=user.admin)

            logger.info(f"User \"{user.username}\" status changed to {status}")
            _hold_u_dur = time.time() - _hold_u_t0
            if _hold_u_dur >= SLOW_USER_TOTAL_THRESHOLD or _t_update_status_hold >= SLOW_STEP_THRESHOLD or _t_start_expire >= SLOW_STEP_THRESHOLD:
                logger.info(
                    f"[review][on_hold][slow] user=\"{user.username}\" total={_hold_u_dur:.3f}s "
                    f"update_status={_t_update_status_hold:.3f}s start_expire={_t_start_expire:.3f}s"
                )
        # Final commit for on_hold group
        _commit_t0 = time.time()
        if changed_onhold_batch > 0:
            logger.warning(f"[review] starting final commit for remaining on_hold size={changed_onhold_batch}")
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit remaining on_hold changes: {e}")
            raise
        finally:
            _commit_dur = time.time() - _commit_t0
            logger.info(f"[review] final commit of on_hold users took {_commit_dur:.3f}s")

    duration = time.time() - start_ts
    logger.info(
        f"review finished in {duration:.2f}s; "
        f"active_checked={checked_active}, applied_next={applied_next}, "
        f"limited={limited_count}, expired={expired_count}, on_hold_activated={on_hold_activated}"
    )


scheduler.add_job(review, 'interval',
                  seconds=JOB_REVIEW_USERS_INTERVAL,
                  coalesce=True, max_instances=1)
