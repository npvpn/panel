from fastapi import APIRouter, Depends, HTTPException

from app.db import Session, crud, get_db
from app.models.admin import Admin
from app.models.bot import (
    BotCreate,
    BotResponse,
    BotSettingsPayload,
    apply_bot_settings_fallback,
)
from app.utils import responses

router = APIRouter(tags=["Bot"], prefix="/api", responses={401: responses._401})


@router.get("/bots", response_model=list[BotResponse])
def get_bots(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    del admin  # explicit auth dependency
    return crud.get_bots(db)


@router.post("/bots", response_model=BotResponse, responses={400: responses._400, 403: responses._403})
def create_bot(
    payload: BotCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin
    try:
        return crud.create_bot(db, payload.username, payload.title)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.delete("/bots/{bot_username}", responses={403: responses._403, 404: responses._404})
def delete_bot(
    bot_username: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin
    bot = crud.get_bot(db, bot_username)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    crud.delete_bot(db, bot)
    return {"detail": "Bot deleted"}


@router.get(
    "/bots/{bot_username}/settings",
    response_model=BotSettingsPayload,
    responses={403: responses._403, 404: responses._404},
)
def get_bot_settings(
    bot_username: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin
    bot = crud.get_bot(db, bot_username)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return apply_bot_settings_fallback(crud.get_bot_settings(db, bot))


@router.put(
    "/bots/{bot_username}/settings",
    response_model=BotSettingsPayload,
    responses={403: responses._403, 404: responses._404},
)
def update_bot_settings(
    bot_username: str,
    payload: BotSettingsPayload,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    del admin
    bot = crud.get_bot(db, bot_username)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    data = payload.model_dump()
    updated = crud.update_bot_settings(db, bot, data)
    return apply_bot_settings_fallback(updated)
