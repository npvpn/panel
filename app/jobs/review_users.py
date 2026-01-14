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
    try:
        xray.operations.update_user(user)
    except Exception as e:
        logger.warning(f"Failed to update user on XRAY during reset_user_by_next for \"{user.username}\": {e}")

    report.user_data_reset_by_next(user=UserResponse.model_validate(user), user_admin=user.admin)


def review():
    now = datetime.utcnow()
    now_ts = now.timestamp()
    start_ts = time.time()
    checked_active = 0
    applied_next = 0
    limited_count = 0
    expired_count = 0
    on_hold_activated = 0
    with GetDB() as db:
        for user in get_users(db, status=UserStatus.active):
            checked_active += 1

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
                    add_notification_reminders(db, user, now)
                continue

            # При недоступности XRAY-нод не допускаем падения задачи: статус все равно обновляем
            try:
                xray.operations.remove_user(user)
            except Exception as e:
                logger.warning(f"Failed to remove user \"{user.username}\" from XRAY: {e}")
            update_user_status(db, user, status, commit=False)

            report.status_change(username=user.username, status=status,
                                 user=UserResponse.model_validate(user), user_admin=user.admin)

            logger.info(f"User \"{user.username}\" status changed to {status}")

        # Коммитим все изменения статусов/next-планов за один раз
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit batched review changes: {e}")
            raise

        for user in get_users(db, status=UserStatus.on_hold):

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

            update_user_status(db, user, status)
            start_user_expire(db, user)
            on_hold_activated += 1

            report.status_change(username=user.username, status=status,
                                 user=UserResponse.model_validate(user), user_admin=user.admin)

            logger.info(f"User \"{user.username}\" status changed to {status}")

    duration = time.time() - start_ts
    logger.info(
        f"review finished in {duration:.2f}s; "
        f"active_checked={checked_active}, applied_next={applied_next}, "
        f"limited={limited_count}, expired={expired_count}, on_hold_activated={on_hold_activated}"
    )


scheduler.add_job(review, 'interval',
                  seconds=JOB_REVIEW_USERS_INTERVAL,
                  coalesce=True, max_instances=1)
