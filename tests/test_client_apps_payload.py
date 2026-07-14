from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.settings import DEFAULT_CLIENT_APPS, ClientAppsPayload, merge_client_apps_defaults


def _payload(**overrides) -> dict:
    base = {
        "apps": [
            {
                "id": "happ",
                "name": "Happ Proxy",
                "scheme": "happ",
                "enabled": True,
                "links": {"android": "https://play.google.com/store/apps/details?id=com.happproxy"},
            }
        ],
        "primary_by_platform": {"android": "happ"},
    }
    base.update(overrides)
    return base


def test_valid_payload_normalizes_missing_links_to_empty_strings():
    payload = ClientAppsPayload.model_validate(_payload())

    assert payload.apps[0].links["ios_ru"] == ""
    assert payload.apps[0].links["android"].startswith("https://")


def test_javascript_scheme_is_rejected():
    with pytest.raises(ValidationError):
        ClientAppsPayload.model_validate(
            _payload(
                apps=[
                    {
                        "id": "evil",
                        "name": "Evil",
                        "scheme": "javascript",
                        "enabled": True,
                        "links": {"android": "javascript:alert(1)"},
                    }
                ],
                primary_by_platform={},
            )
        )


def test_non_http_link_is_rejected():
    with pytest.raises(ValidationError):
        ClientAppsPayload.model_validate(
            _payload(
                apps=[
                    {
                        "id": "happ",
                        "name": "Happ Proxy",
                        "scheme": "happ",
                        "enabled": True,
                        "links": {"android": "ftp://example.com/app.apk"},
                    }
                ]
            )
        )


def test_duplicate_app_id_is_rejected():
    app = {"id": "happ", "name": "Happ", "scheme": "happ", "enabled": True, "links": {}}
    with pytest.raises(ValidationError):
        ClientAppsPayload.model_validate(_payload(apps=[app, dict(app)], primary_by_platform={}))


def test_primary_pointing_to_unknown_app_is_rejected():
    with pytest.raises(ValidationError):
        ClientAppsPayload.model_validate(_payload(primary_by_platform={"android": "nope"}))


def test_primary_pointing_to_disabled_app_is_rejected():
    with pytest.raises(ValidationError):
        ClientAppsPayload.model_validate(
            _payload(
                apps=[
                    {
                        "id": "happ",
                        "name": "Happ Proxy",
                        "scheme": "happ",
                        "enabled": False,
                        "links": {"android": "https://play.google.com/store/apps/details?id=com.happproxy"},
                    }
                ]
            )
        )


def test_merge_returns_defaults_for_empty_raw():
    assert merge_client_apps_defaults(None) == DEFAULT_CLIENT_APPS
    assert merge_client_apps_defaults({}) == DEFAULT_CLIENT_APPS


def test_merge_falls_back_to_defaults_on_broken_data():
    assert merge_client_apps_defaults({"apps": "garbage"}) == DEFAULT_CLIENT_APPS


def test_defaults_are_valid():
    ClientAppsPayload.model_validate(DEFAULT_CLIENT_APPS)
