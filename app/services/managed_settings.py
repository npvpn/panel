from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.models.settings import CLIENT_APPS_KEY, ClientAppsPayload

if TYPE_CHECKING:
    # Отложенный импорт: app.db тянет SQLAlchemy-модели и подключение к БД,
    # которые не нужны чистой функции validate_managed_payload и не должны
    # тянуться при импорте модуля (см. crud-функции ниже — там app.db
    # импортируется лениво, внутри функций, которым реально нужна db).
    from app.db import Session


@dataclass(frozen=True)
class ManagedSection:
    key: str
    scope: str
    validate: Callable[[dict[str, Any]], dict[str, Any]]


def _validate_client_apps(data: dict[str, Any]) -> dict[str, Any]:
    return ClientAppsPayload.model_validate(data).model_dump()


MANAGED_SECTIONS: dict[str, ManagedSection] = {
    CLIENT_APPS_KEY: ManagedSection(key=CLIENT_APPS_KEY, scope="global", validate=_validate_client_apps),
}


def validate_managed_payload(key: str, data: dict[str, Any]) -> dict[str, Any]:
    section = MANAGED_SECTIONS[key]  # KeyError для неизвестного ключа
    return section.validate(data)


def apply_managed_push(db: Session, key: str, *, data: dict[str, Any], version: str, source: str) -> dict[str, Any]:
    from app.db import crud

    section = MANAGED_SECTIONS[key]
    normalized = section.validate(data)
    crud.upsert_global_setting(db, key, normalized)
    return _as_state(crud.upsert_managed_setting(db, key, scope=section.scope, source=source, version=version))


def read_managed_state(db: Session, key: str) -> dict[str, Any] | None:
    from app.db import crud

    row = crud.get_managed_setting(db, key)
    return _as_state(row) if row else None


def unlink_managed(db: Session, key: str) -> bool:
    from app.db import crud

    return crud.delete_managed_setting(db, key)


def _as_state(row: dict[str, Any]) -> dict[str, Any]:
    return {"key": row["key"], "version": row["version"], "source": row["source"], "applied_at": row["applied_at"]}
