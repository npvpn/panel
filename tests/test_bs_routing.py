import pytest

from app.xray.bs_routing import parse_json_object, select_routing


def test_parse_empty_returns_none():
    assert parse_json_object("") is None
    assert parse_json_object("   ") is None
    assert parse_json_object(None) is None


def test_parse_valid_object():
    assert parse_json_object('{"rules": [1, 2]}') == {"rules": [1, 2]}


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_json_object("{not json")


def test_parse_non_object_raises():
    with pytest.raises(ValueError):
        parse_json_object("[1, 2, 3]")


def test_select_routing_bs_uses_bs_block():
    tmpl = {"rules": ["tmpl"]}
    rdef = {"rules": ["default"]}
    rbs = {"rules": ["bs"]}
    assert select_routing(tmpl, rdef, rbs, is_bs=True) == rbs


def test_select_routing_default_uses_default_block():
    tmpl = {"rules": ["tmpl"]}
    rdef = {"rules": ["default"]}
    rbs = {"rules": ["bs"]}
    assert select_routing(tmpl, rdef, rbs, is_bs=False) == rdef


def test_select_routing_bs_falls_back_to_template_when_no_bs_block():
    tmpl = {"rules": ["tmpl"]}
    assert select_routing(tmpl, None, None, is_bs=True) == tmpl


def test_select_routing_default_falls_back_to_template_when_no_default_block():
    tmpl = {"rules": ["tmpl"]}
    assert select_routing(tmpl, None, None, is_bs=False) == tmpl
