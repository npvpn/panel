from __future__ import annotations

import importlib.util
import pathlib

from app.models.settings import DEFAULT_CLIENT_APPS

MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "app" / "db" / "migrations" / "versions"


def _load_seed() -> dict:
    matches = sorted(MIGRATIONS_DIR.glob("*_add_global_settings.py"))
    assert len(matches) == 1, f"expected exactly one global_settings migration, got {matches}"

    spec = importlib.util.spec_from_file_location("migration_global_settings", matches[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SEED_CLIENT_APPS


def test_migration_seed_matches_defaults():
    assert _load_seed() == DEFAULT_CLIENT_APPS
