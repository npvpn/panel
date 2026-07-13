from fastapi import APIRouter, Depends

from app.db import Session, get_db
from app.models.admin import Admin
from app.models.settings import DEFAULT_CLIENT_APPS, ClientAppsPayload
from app.services import client_apps as client_apps_service
from app.utils import responses

router = APIRouter(tags=["Settings"], prefix="/api", responses={401: responses._401})


@router.get("/settings/apps", response_model=ClientAppsPayload, responses={403: responses._403})
def get_client_apps(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin  # explicit auth dependency
    return client_apps_service.get_client_apps(db)


@router.put("/settings/apps", response_model=ClientAppsPayload, responses={403: responses._403})
def update_client_apps(
    payload: ClientAppsPayload,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin
    return client_apps_service.save_client_apps(db, payload)


@router.get("/settings/apps/defaults", response_model=ClientAppsPayload, responses={403: responses._403})
def get_default_client_apps(
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin
    return DEFAULT_CLIENT_APPS
