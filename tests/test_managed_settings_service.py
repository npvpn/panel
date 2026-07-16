import pytest

from app.models.settings import DEFAULT_CLIENT_APPS
from app.services.managed_settings import validate_managed_payload


def test_validate_known_key_normalizes():
    result = validate_managed_payload("client_apps", DEFAULT_CLIENT_APPS)
    assert "apps" in result and "primary_by_platform" in result


def test_validate_unknown_key_raises():
    with pytest.raises(KeyError):
        validate_managed_payload("nope", {})


def test_validate_broken_payload_raises():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        validate_managed_payload(
            "client_apps", {"apps": [{"id": "x", "enabled": True}], "primary_by_platform": {"ios": "x"}}
        )
