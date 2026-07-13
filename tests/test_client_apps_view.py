from __future__ import annotations

import copy

from app.models.settings import DEFAULT_CLIENT_APPS
from app.subscription.client_apps import build_client_apps_view


def test_defaults_reproduce_current_page():
    view = build_client_apps_view(None)["platforms"]

    # На iOS главным сейчас является Incy (у Happ нет ru-ссылки), на Android — Happ.
    assert view["ios"]["primary"]["id"] == "incy"
    assert view["ios"]["primary"]["scheme"] == "incy"
    assert view["android"]["primary"]["id"] == "happ"

    ios_regions = [item["region"] for item in view["ios"]["primary"]["install"]]
    assert ios_regions == ["ru", "global"]

    # У Happ на iOS осталась только глобальная ссылка — он альтернатива с одной кнопкой.
    ios_alternatives = {app["id"]: app for app in view["ios"]["alternatives"]}
    assert [item["region"] for item in ios_alternatives["happ"]["install"]] == ["global"]

    # v2RayTun ссылок под iOS не имеет — его на этой платформе нет вообще.
    assert "v2raytun" not in ios_alternatives

    android_alternatives = [app["id"] for app in view["android"]["alternatives"]]
    assert android_alternatives == ["incy", "v2raytun"]


def test_platform_without_links_has_no_apps():
    view = build_client_apps_view(None)["platforms"]

    # Linux есть только у Happ.
    assert view["linux"]["primary"]["id"] == "happ"
    assert view["linux"]["alternatives"] == []


def test_disabled_app_disappears_from_view():
    raw = copy.deepcopy(DEFAULT_CLIENT_APPS)
    for app in raw["apps"]:
        if app["id"] == "v2raytun":
            app["enabled"] = False

    view = build_client_apps_view(raw)["platforms"]

    assert [app["id"] for app in view["android"]["alternatives"]] == ["incy"]


def test_empty_link_hides_button():
    raw = copy.deepcopy(DEFAULT_CLIENT_APPS)
    for app in raw["apps"]:
        if app["id"] == "incy":
            app["links"]["ios_ru"] = ""

    view = build_client_apps_view(raw)["platforms"]

    assert [item["region"] for item in view["ios"]["primary"]["install"]] == ["global"]


def test_primary_without_links_is_replaced_by_first_alternative():
    raw = copy.deepcopy(DEFAULT_CLIENT_APPS)
    for app in raw["apps"]:
        if app["id"] == "incy":
            app["links"]["ios_ru"] = ""
            app["links"]["ios_global"] = ""

    view = build_client_apps_view(raw)["platforms"]

    # У Incy на iOS не осталось ни одной ссылки — главным становится Happ.
    assert view["ios"]["primary"]["id"] == "happ"
