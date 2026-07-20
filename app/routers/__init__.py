from fastapi import APIRouter

from . import (
    admin,
    bot,
    core,
    home,
    managed,
    node,
    settings,
    subscription,
    system,
    user,
    user_template,
)

api_router = APIRouter()

routers: list[APIRouter] = [
    admin.router,
    bot.router,
    core.router,
    managed.router,  # type: ignore[has-type]
    node.router,
    settings.router,  # type: ignore[has-type]
    subscription.router,
    system.router,
    user_template.router,
    user.router,
    home.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]
