from __future__ import annotations

from app.subscription.headers import build_content_disposition, get_routing_header


def test_routing_header_for_happ():
    settings = {"sub_routing_happ": "happ-routing", "sub_routing_v2raytun": "v2raytun-routing"}

    assert get_routing_header("Happ/1.2.3", settings) == {"routing": "happ-routing"}


def test_routing_header_for_v2raytun():
    settings = {"sub_routing_happ": "happ-routing", "sub_routing_v2raytun": "v2raytun-routing"}

    assert get_routing_header("v2rayTun/1.0", settings) == {"routing": "v2raytun-routing"}


def test_routing_header_is_empty_for_unknown_client():
    assert get_routing_header("Mozilla/5.0", {"sub_routing_happ": "x"}) == {}


def test_content_disposition_contains_username():
    assert "user1" in build_content_disposition("user1")
