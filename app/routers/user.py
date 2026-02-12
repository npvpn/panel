from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from app import logger, xray
from app.db import Session, crud, get_db
from app.dependencies import get_expired_users_list, get_validated_user, validate_dates
from app.models.admin import Admin
from app.models.user import (
    UserCreate,
    UserDeviceCreate,
    UserDeviceResponse,
    UserDevicesResponse,
    UserDeviceUpdate,
    UserModify,
    UserResponse,
    UsersResponse,
    UserStatus,
    UsersUsagesResponse,
    UserUsagesResponse,
)
from app.utils import report, responses
from app.db.models import Proxy as DBProxy
from app.models.proxy import (
    ProxyTypes,
    VMessSettings,
    VLESSSettings,
    TrojanSettings,
    ShadowsocksSettings,
    XTLSFlows,
)

router = APIRouter(tags=["User"], prefix="/api", responses={401: responses._401})

SYNC_PROGRESS = {}

def _run_update_and_mark(user_id: int, op_id: str):
    """
    Background helper to update user and mark progress counters.
    """
    try:
        from app.db import GetDB
        with GetDB() as db:
            dbuser = crud.get_user_by_id(db, user_id)
            if not dbuser:
                return
            try:
                xray.operations.update_user(dbuser)
            finally:
                try:
                    st = SYNC_PROGRESS.get(op_id)
                    if st:
                        st["done"] = st.get("done", 0) + 1
                        if st["done"] >= st.get("scheduled", 0):
                            st["running"] = False
                            st["finished_at"] = datetime.utcnow().isoformat()
                except Exception:
                    pass
    except Exception:
        # ignore any exceptions to not break background runner, but still count as done
        try:
            st = SYNC_PROGRESS.get(op_id)
            if st:
                st["done"] = st.get("done", 0) + 1
                if st["done"] >= st.get("scheduled", 0):
                    st["running"] = False
                    st["finished_at"] = datetime.utcnow().isoformat()
        except Exception:
            pass


@router.post("/user", response_model=UserResponse, responses={400: responses._400, 409: responses._409})
def add_user(
    new_user: UserCreate,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Add a new user

    - **username**: 3 to 32 characters, can include a-z, 0-9, and underscores.
    - **status**: User's status, defaults to `active`. Special rules if `on_hold`.
    - **expire**: UTC timestamp for account expiration. Use `0` for unlimited.
    - **data_limit**: Max data usage in bytes (e.g., `1073741824` for 1GB). `0` means unlimited.
    - **data_limit_reset_strategy**: Defines how/if data limit resets. `no_reset` means it never resets.
    - **proxies**: Dictionary of protocol settings (e.g., `vmess`, `vless`).
    - **inbounds**: Dictionary of protocol tags to specify inbound connections.
    - **note**: Optional text field for additional user information or notes.
    - **on_hold_timeout**: UTC timestamp when `on_hold` status should start or end.
    - **on_hold_expire_duration**: Duration (in seconds) for how long the user should stay in `on_hold` status.
    - **next_plan**: Next user plan (resets after use).
    """

    # TODO expire should be datetime instead of timestamp

    for proxy_type in new_user.proxies:
        if not xray.config.inbounds_by_protocol.get(proxy_type):
            raise HTTPException(
                status_code=400,
                detail=f"Protocol {proxy_type} is disabled on your server",
            )

    try:
        dbuser = crud.create_user(
            db, new_user, admin=crud.get_admin(db, admin.username)
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")

    bg.add_task(xray.operations.add_user, dbuser=dbuser)
    user = UserResponse.model_validate(dbuser)
    report.user_created(user=user, user_id=dbuser.id, by=admin, user_admin=dbuser.admin)
    logger.info(f'New user "{dbuser.username}" added')
    return user


@router.get("/user/{username}", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def get_user(db: Session = Depends(get_db), dbuser: UserResponse = Depends(get_validated_user)):
    """Get user information"""
    crud.ensure_subscription_token(db, dbuser)
    return UserResponse.model_validate(dbuser)


@router.get(
    "/user/{username}/devices",
    response_model=UserDevicesResponse,
    responses={403: responses._403, 404: responses._404},
)
def list_user_devices(
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    devices = crud.get_user_devices(db, dbuser)
    return {"devices": devices}


@router.post(
    "/user/{username}/devices",
    response_model=UserDeviceResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404, 409: responses._409},
)
def add_user_device(
    device: UserDeviceCreate,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    if dbuser.device_limit and crud.count_user_devices(db, dbuser) >= dbuser.device_limit:
        raise HTTPException(status_code=403, detail="Device limit reached")
    try:
        dbdevice = crud.create_user_device(db, dbuser, device)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Device already exists")
    return dbdevice


@router.put(
    "/user/{username}/devices/{device_id}",
    response_model=UserDeviceResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404, 409: responses._409},
)
def update_user_device(
    device_id: int,
    device: UserDeviceUpdate,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    dbdevice = crud.get_user_device(db, dbuser, device_id)
    if not dbdevice:
        raise HTTPException(status_code=404, detail="Device not found")
    if device.hwid:
        existing = crud.get_user_device_by_hwid(db, dbuser, device.hwid)
        if existing and existing.id != dbdevice.id:
            raise HTTPException(status_code=409, detail="Device already exists")
    try:
        return crud.update_user_device(db, dbdevice, device)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Device already exists")


@router.delete(
    "/user/{username}/devices/{device_id}",
    responses={403: responses._403, 404: responses._404},
)
def delete_user_device(
    device_id: int,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    dbdevice = crud.get_user_device(db, dbuser, device_id)
    if not dbdevice:
        raise HTTPException(status_code=404, detail="Device not found")
    crud.delete_user_device(db, dbdevice)
    return {"detail": "Device successfully deleted"}


@router.put("/user/{username}", response_model=UserResponse, responses={400: responses._400, 403: responses._403, 404: responses._404})
def modify_user(
    modified_user: UserModify,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UsersResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Modify an existing user

    - **username**: Cannot be changed. Used to identify the user.
    - **status**: User's new status. Can be 'active', 'disabled', 'on_hold', 'limited', or 'expired'.
    - **expire**: UTC timestamp for new account expiration. Set to `0` for unlimited, `null` for no change.
    - **data_limit**: New max data usage in bytes (e.g., `1073741824` for 1GB). Set to `0` for unlimited, `null` for no change.
    - **data_limit_reset_strategy**: New strategy for data limit reset. Options include 'daily', 'weekly', 'monthly', or 'no_reset'.
    - **proxies**: Dictionary of new protocol settings (e.g., `vmess`, `vless`). Empty dictionary means no change.
    - **inbounds**: Dictionary of new protocol tags to specify inbound connections. Empty dictionary means no change.
    - **note**: New optional text for additional user information or notes. `null` means no change.
    - **on_hold_timeout**: New UTC timestamp for when `on_hold` status should start or end. Only applicable if status is changed to 'on_hold'.
    - **on_hold_expire_duration**: New duration (in seconds) for how long the user should stay in `on_hold` status. Only applicable if status is changed to 'on_hold'.
    - **next_plan**: Next user plan (resets after use).

    Note: Fields set to `null` or omitted will not be modified.
    """

    for proxy_type in modified_user.proxies:
        if not xray.config.inbounds_by_protocol.get(proxy_type):
            raise HTTPException(
                status_code=400,
                detail=f"Protocol {proxy_type} is disabled on your server",
            )

    old_status = dbuser.status
    dbuser = crud.update_user(db, dbuser, modified_user)
    user = UserResponse.model_validate(dbuser)

    if user.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.update_user, dbuser=dbuser)
    else:
        bg.add_task(xray.operations.remove_user, dbuser=dbuser)

    bg.add_task(report.user_updated, user=user, user_admin=dbuser.admin, by=admin)

    logger.info(f'User "{user.username}" modified')

    if user.status != old_status:
        bg.add_task(
            report.status_change,
            username=user.username,
            status=user.status,
            user=user,
            user_admin=dbuser.admin,
            by=admin,
        )
        logger.info(
            f'User "{dbuser.username}" status changed from {old_status} to {user.status}'
        )

    return user


@router.delete("/user/{username}", responses={403: responses._403, 404: responses._404})
def remove_user(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """Remove a user"""
    crud.remove_user(db, dbuser)
    bg.add_task(xray.operations.remove_user, dbuser=dbuser)

    bg.add_task(
        report.user_deleted, username=dbuser.username, user_admin=Admin.model_validate(dbuser.admin), by=admin
    )

    logger.info(f'User "{dbuser.username}" deleted')
    return {"detail": "User successfully deleted"}


@router.post("/user/{username}/reset", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def reset_user_data_usage(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """Reset user data usage"""
    dbuser = crud.reset_user_data_usage(db=db, dbuser=dbuser)
    if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.add_user, dbuser=dbuser)

    user = UserResponse.model_validate(dbuser)
    bg.add_task(
        report.user_data_usage_reset, user=user, user_admin=dbuser.admin, by=admin
    )

    logger.info(f'User "{dbuser.username}"\'s usage was reset')
    return dbuser


@router.post("/user/{username}/revoke_sub", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def revoke_user_subscription(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """Revoke users subscription (Subscription link and proxies)"""
    dbuser = crud.revoke_user_sub(db=db, dbuser=dbuser)

    if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.update_user, dbuser=dbuser)
    user = UserResponse.model_validate(dbuser)
    bg.add_task(
        report.user_subscription_revoked, user=user, user_admin=dbuser.admin, by=admin
    )

    logger.info(f'User "{dbuser.username}" subscription revoked')

    return user


@router.get("/users", response_model=UsersResponse, responses={400: responses._400, 403: responses._403, 404: responses._404})
def get_users(
    offset: int = None,
    limit: int = None,
    username: List[str] = Query(None),
    search: Union[str, None] = None,
    owner: Union[List[str], None] = Query(None, alias="admin"),
    status: UserStatus = None,
    sort: str = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Get all users"""
    if sort is not None:
        opts = sort.strip(",").split(",")
        sort = []
        for opt in opts:
            try:
                sort.append(crud.UsersSortingOptions[opt])
            except KeyError:
                raise HTTPException(
                    status_code=400, detail=f'"{opt}" is not a valid sort option'
                )

    users, count = crud.get_users(
        db=db,
        offset=offset,
        limit=limit,
        search=search,
        usernames=username,
        status=status,
        sort=sort,
        admins=owner if admin.is_sudo else [admin.username],
        return_with_count=True,
    )
    # Ensure tokens for legacy users to populate subscription_url in UI
    for u in users:
        crud.ensure_subscription_token(db, u)
    return {"users": users, "total": count}


@router.post("/users/reset", responses={403: responses._403, 404: responses._404})
def reset_users_data_usage(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Reset all users data usage"""
    dbadmin = crud.get_admin(db, admin.username)
    crud.reset_all_users_data_usage(db=db, admin=dbadmin)
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    return {"detail": "Users successfully reset."}


@router.post("/users/sync-inbounds", responses={403: responses._403})
def sync_users_inbounds(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """
    Sync active users' inbounds with the global XRay configuration:
    - Add any missing inbounds that exist globally (by clearing exclusions)
    - Remove any stale exclusions for non-existent inbounds
    """
    logger.info("[sync-inbounds] started by %s", admin.username)
    op_id = uuid4().hex
    users = crud.get_users(db=db, status=UserStatus.active)
    users_updated = 0
    users_scheduled = 0
    SYNC_PROGRESS[op_id] = {
        "running": True,
        "started_at": datetime.utcnow().isoformat(),
        "users_processed": 0,
        "users_updated": 0,
        "scheduled": 0,
        "done": 0,
        "total": len(users),
        "by": admin.username,
    }

    for dbuser in users:
        changed = False
        # 1) Ensure all globally-enabled protocols exist for the user
        try:
            existing_types = {p.type for p in dbuser.proxies}
        except Exception:
            existing_types = set()
        global_protocols = [
            ProxyTypes(p) for p, inbounds in xray.config.inbounds_by_protocol.items() if inbounds
        ]
        missing_protocols = [p for p in global_protocols if p not in existing_types]
        for protocol in missing_protocols:
            # Generate default settings per protocol
            if protocol == ProxyTypes.VLESS:
                settings = VLESSSettings(flow=XTLSFlows.VISION)  # prefer vision; will be sanitized if incompatible
            elif protocol == ProxyTypes.VMess:
                settings = VMessSettings()
            elif protocol == ProxyTypes.Shadowsocks:
                settings = ShadowsocksSettings()
            elif protocol == ProxyTypes.Trojan:
                settings = TrojanSettings()
            else:
                continue

            dbuser.proxies.append(DBProxy(type=protocol, settings=settings.dict(no_obj=True)))
            changed = True
            logger.info('[sync-inbounds] added missing protocol=%s for user="%s"', protocol.value, dbuser.username)

        for proxy in dbuser.proxies:
            # Determine global inbound tags for this protocol
            global_inbounds = xray.config.inbounds_by_protocol.get(
                proxy.type if isinstance(proxy.type, str) else proxy.type.value, []
            )
            global_tags = {i["tag"] for i in global_inbounds}

            # If there are any exclusions, clear exclusions to include all global inbounds
            if proxy.excluded_inbounds:
                before_tags = [i.tag for i in proxy.excluded_inbounds]
                before_count = len(before_tags)
                # Also drop any stale exclusions that no longer exist globally
                filtered_exclusions = [
                    inbound for inbound in proxy.excluded_inbounds if inbound.tag in global_tags
                ]
                cleared = bool(filtered_exclusions)
                if filtered_exclusions:
                    # We want users to have ALL global inbounds -> clear remaining exclusions
                    proxy.excluded_inbounds = []
                changed = True
                logger.info(
                    "[sync-inbounds] user=%s protocol=%s excl_before=%d global_tags=%d cleared=%s",
                    dbuser.username,
                    str(proxy.type),
                    before_count,
                    len(global_tags),
                    str(cleared),
                )

        if changed:
            users_updated += 1
        # Apply to running cores for active/on-hold users regardless of DB change,
        # so newly added/removed global inbounds reflect in runtime.
        if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
            users_scheduled += 1
            SYNC_PROGRESS[op_id]["scheduled"] = users_scheduled
            bg.add_task(_run_update_and_mark, user_id=dbuser.id, op_id=op_id)
            logger.info('[sync-inbounds] queued update_user for user="%s"', dbuser.username)
        SYNC_PROGRESS[op_id]["users_processed"] += 1

    if users_updated:
        db.commit()

    result = {
        "detail": "Inbounds synchronized with global configuration.",
        "users_processed": len(users),
        "users_updated": users_updated,
        "users_scheduled": users_scheduled,
        "op_id": op_id,
    }
    logger.info(
        "[sync-inbounds] finished users_processed=%d users_updated=%d users_scheduled=%d",
        result["users_processed"],
        result["users_updated"],
        result["users_scheduled"],
    )
    return result


@router.get("/users/sync-inbounds/status")
def get_sync_inbounds_status(op_id: str = None, admin: Admin = Depends(Admin.get_current)):
    """
    Returns status of a sync operation. If op_id is not provided, returns the latest one for this admin (if any).
    """
    if not SYNC_PROGRESS:
        return {"detail": "no sync running"}
    if not op_id:
        # pick latest entry for this admin
        latest = None
        for k, v in SYNC_PROGRESS.items():
            if v.get("by") != admin.username:
                continue
            if latest is None or v.get("started_at", "") > SYNC_PROGRESS[latest].get("started_at", ""):
                latest = k
        if not latest:
            return {"detail": "no sync found for this admin"}
        op_id = latest
    st = SYNC_PROGRESS.get(op_id)
    if not st:
        return {"detail": "not found"}
    return {"op_id": op_id, **st}


@router.get("/user/{username}/usage", response_model=UserUsagesResponse, responses={403: responses._403, 404: responses._404})
def get_user_usage(
    dbuser: UserResponse = Depends(get_validated_user),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db),
):
    """Get users usage"""
    start, end = validate_dates(start, end)

    usages = crud.get_user_usages(db, dbuser, start, end)

    return {"usages": usages, "username": dbuser.username}


@router.post("/user/{username}/active-next", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def active_next_plan(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
):
    """Reset user by next plan"""
    dbuser = crud.reset_user_by_next(db=db, dbuser=dbuser)

    if (dbuser is None or dbuser.next_plan is None):
        raise HTTPException(
            status_code=404,
            detail=f"User doesn't have next plan",
        )

    if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.add_user, dbuser=dbuser)

    user = UserResponse.model_validate(dbuser)
    bg.add_task(
        report.user_data_reset_by_next, user=user, user_admin=dbuser.admin,
    )

    logger.info(f'User "{dbuser.username}"\'s usage was reset by next plan')
    return dbuser


@router.get("/users/usage", response_model=UsersUsagesResponse)
def get_users_usage(
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db),
    owner: Union[List[str], None] = Query(None, alias="admin"),
    admin: Admin = Depends(Admin.get_current),
):
    """Get all users usage"""
    start, end = validate_dates(start, end)

    usages = crud.get_all_users_usages(
        db=db, start=start, end=end, admin=owner if admin.is_sudo else [admin.username]
    )

    return {"usages": usages}


@router.put("/user/{username}/set-owner", response_model=UserResponse)
def set_owner(
    admin_username: str,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Set a new owner (admin) for a user."""
    new_admin = crud.get_admin(db, username=admin_username)
    if not new_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    dbuser = crud.set_owner(db, dbuser, new_admin)
    user = UserResponse.model_validate(dbuser)

    logger.info(f'{user.username}"owner successfully set to{admin.username}')

    return user


@router.get("/users/expired", response_model=List[str])
def get_expired_users(
    expired_after: Optional[datetime] = Query(None, example="2024-01-01T00:00:00"),
    expired_before: Optional[datetime] = Query(None, example="2024-01-31T23:59:59"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Get users who have expired within the specified date range.

    - **expired_after** UTC datetime (optional)
    - **expired_before** UTC datetime (optional)
    - At least one of expired_after or expired_before must be provided for filtering
    - If both are omitted, returns all expired users
    """

    expired_after, expired_before = validate_dates(expired_after, expired_before)

    expired_users = get_expired_users_list(db, admin, expired_after, expired_before)
    return [u.username for u in expired_users]


@router.delete("/users/expired", response_model=List[str])
def delete_expired_users(
    bg: BackgroundTasks,
    expired_after: Optional[datetime] = Query(None, example="2024-01-01T00:00:00"),
    expired_before: Optional[datetime] = Query(None, example="2024-01-31T23:59:59"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Delete users who have expired within the specified date range.

    - **expired_after** UTC datetime (optional)
    - **expired_before** UTC datetime (optional)
    - At least one of expired_after or expired_before must be provided
    """
    expired_after, expired_before = validate_dates(expired_after, expired_before)

    expired_users = get_expired_users_list(db, admin, expired_after, expired_before)
    removed_users = [u.username for u in expired_users]

    if not removed_users:
        raise HTTPException(
            status_code=404, detail="No expired users found in the specified date range"
        )

    crud.remove_users(db, expired_users)

    for removed_user in removed_users:
        logger.info(f'User "{removed_user}" deleted')
        bg.add_task(
            report.user_deleted,
            username=removed_user,
            user_admin=next(
                (u.admin for u in expired_users if u.username == removed_user), None
            ),
            by=admin,
        )

    return removed_users
