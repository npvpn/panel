from typing import Any, Dict

from app.db.models import User
from app.models.bot import apply_bot_settings_fallback


def resolve_bot_settings(user: User) -> Dict[str, Any]:
    if user and user.bot and user.bot.settings:
        return apply_bot_settings_fallback(user.bot.settings.data)
    return apply_bot_settings_fallback(None)
