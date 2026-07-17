from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.db import Session, get_db
from app.models.admin import Admin
from app.models.managed import ManagedPushRequest, ManagedStateResponse
from app.services import managed_settings as svc
from app.utils import responses

router = APIRouter(tags=["Managed"], prefix="/api", responses={401: responses._401})


@router.put("/managed/{key}", response_model=ManagedStateResponse)
def push_managed(
    key: str,
    payload: ManagedPushRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    del admin
    if key not in svc.MANAGED_SECTIONS:
        raise HTTPException(status_code=404, detail="unknown managed key")
    try:
        state = svc.apply_managed_push(db, key, data=payload.data, version=payload.version, source=payload.source)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    return state


@router.get("/managed/{key}", response_model=ManagedStateResponse)
def get_managed(
    key: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    del admin
    state = svc.read_managed_state(db, key)
    if state is None:
        raise HTTPException(status_code=404, detail="not managed")
    return state


@router.delete("/managed/{key}")
def delete_managed(
    key: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    del admin
    removed = svc.unlink_managed(db, key)
    return {"key": key, "unlinked": removed}
