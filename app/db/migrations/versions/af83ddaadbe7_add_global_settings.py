"""add global settings

Revision ID: af83ddaadbe7
Revises: e976cad65b63
Create Date: 2026-07-13 14:46:18.756141

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af83ddaadbe7'
down_revision = 'e976cad65b63'
branch_labels = None
depends_on = None

# Значения повторяют DEFAULT_CLIENT_APPS из app/models/settings.py.
# Дублирование намеренное: миграция обязана быть самодостаточной и не зависеть от кода,
# который со временем изменится. Совпадение стережёт tests/test_client_apps_defaults.py.
_HAPP_APPSTORE_GLOBAL = "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"
_INCY_APPSTORE_RU = "https://apps.apple.com/ru/app/incy/id6756943388"
_INCY_APPSTORE_GLOBAL = "https://apps.apple.com/us/app/incy/id6756943388"

SEED_CLIENT_APPS = {
    "apps": [
        {
            "id": "happ",
            "name": "Happ Proxy",
            "scheme": "happ",
            "enabled": True,
            "links": {
                "ios_ru": "",
                "ios_global": _HAPP_APPSTORE_GLOBAL,
                "macos_ru": "",
                "macos_global": _HAPP_APPSTORE_GLOBAL,
                "android": "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru",
                "androidtv": "https://play.google.com/store/apps/details?id=com.happproxy",
                "windows": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe",
                "linux": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.linux.x64.deb",
            },
        },
        {
            "id": "incy",
            "name": "Incy",
            "scheme": "incy",
            "enabled": True,
            "links": {
                "ios_ru": _INCY_APPSTORE_RU,
                "ios_global": _INCY_APPSTORE_GLOBAL,
                "macos_ru": _INCY_APPSTORE_RU,
                "macos_global": _INCY_APPSTORE_GLOBAL,
                "android": "https://play.google.com/store/apps/details?id=llc.itdev.incy",
                "androidtv": "",
                "windows": "https://incy.cc/",
                "linux": "",
            },
        },
        {
            "id": "v2raytun",
            "name": "v2RayTun",
            "scheme": "v2raytun",
            "enabled": True,
            "links": {
                "ios_ru": "",
                "ios_global": "",
                "macos_ru": "",
                "macos_global": "",
                "android": "https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru",
                "androidtv": "",
                "windows": "https://v2raytun.com/",
                "linux": "",
            },
        },
    ],
    "primary_by_platform": {
        "ios": "incy",
        "macos": "incy",
        "android": "happ",
        "windows": "happ",
        "linux": "happ",
        "androidtv": "happ",
    },
}


def upgrade() -> None:
    global_settings = op.create_table(
        "global_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(global_settings, [{"key": "client_apps", "data": SEED_CLIENT_APPS}])


def downgrade() -> None:
    op.drop_table("global_settings")
