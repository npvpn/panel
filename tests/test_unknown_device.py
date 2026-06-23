"""Unknown-устройства без hwid: сопоставление UA и сценарии register_user_device."""

from __future__ import annotations

import pytest

from app.subscription.device_ua import unknown_user_agents_match


def _no_hwid_registration(stored_ua: str | None, incoming_ua: str | None) -> tuple[bool, bool]:
    """Исход register_user_device для ветки без hwid, если unknown-устройство уже есть."""
    if unknown_user_agents_match(stored_ua, incoming_ua):
        return True, False
    return False, True


@pytest.mark.parametrize(
    ("stored", "incoming", "expected"),
    [
        ("Неизвестно", "Happ/3.23.0/Android", True),
        (None, "Happ/3.23.0/Android", True),
        ("", "Happ/3.23.0/Android", True),
        ("   ", "Happ/3.23.0/Android", True),
        ("Happ/3.23.0/Android", "Happ/3.23.0/Android", True),
        ("Happ/3.23.0/Android", "  Happ/3.23.0/Android  ", True),
        ("Happ/3.23.0/Android", "v2raytun/android", False),
        ("Happ/3.23.0/Android", None, False),
        ("Happ/3.23.0/Android", "", False),
        (None, None, True),
    ],
)
def test_unknown_user_agents_match(stored, incoming, expected):
    """Legacy placeholder UA принимает любой клиент; после привязки — только тот же UA."""
    assert unknown_user_agents_match(stored, incoming) is expected


@pytest.mark.parametrize(
    ("stored", "incoming", "registered", "unsupported"),
    [
        ("Неизвестно", "Happ/3.23.0/Android", True, False),
        (None, "Happ/3.23.0/Android", True, False),
        ("Happ/3.23.0/Android", "Happ/3.23.0/Android", True, False),
        ("Happ/3.23.0/Android", "v2raytun/android", False, True),
        ("Happ/3.23.0/Android", "Mozilla/5.0 Chrome", False, True),
    ],
)
def test_no_hwid_unknown_device_registration_outcome(stored, incoming, registered, unsupported):
    """Без hwid: unsupported только если unknown-устройство уже есть и UA другой."""
    assert _no_hwid_registration(stored, incoming) == (registered, unsupported)
