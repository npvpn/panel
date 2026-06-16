import copy

from app.xray.bs_limit import (
    period_keys,
    bs_counter_step,
    diff_blocks,
    strip_blocked_clients,
)


class FakeConfig(dict):
    def copy(self):
        return FakeConfig(copy.deepcopy(dict(self)))


def base():
    return FakeConfig({
        "inbounds": [
            {"tag": "VLESS_TCP", "settings": {"clients": [
                {"email": "1.alice"}, {"email": "2.bob"}, {"email": "10.carol"}]}},
            {"tag": "NO_SETTINGS"},
        ],
    })


def test_period_keys_formats_day_and_month():
    from datetime import datetime
    assert period_keys(datetime(2026, 6, 16, 13, 5)) == ("2026-06-16", "2026-06")


def test_counter_step_fresh_row_starts_from_delta():
    r = bs_counter_step(None, 100, "2026-06-16", "2026-06")
    assert r == {"daily_used": 100, "daily_period": "2026-06-16",
                 "monthly_used": 100, "monthly_period": "2026-06"}


def test_counter_step_same_period_accumulates():
    existing = {"daily_used": 100, "daily_period": "2026-06-16",
                "monthly_used": 500, "monthly_period": "2026-06"}
    r = bs_counter_step(existing, 30, "2026-06-16", "2026-06")
    assert r["daily_used"] == 130 and r["monthly_used"] == 530


def test_counter_step_new_day_resets_daily_keeps_month():
    existing = {"daily_used": 100, "daily_period": "2026-06-16",
                "monthly_used": 500, "monthly_period": "2026-06"}
    r = bs_counter_step(existing, 30, "2026-06-17", "2026-06")
    assert r["daily_used"] == 30 and r["daily_period"] == "2026-06-17"
    assert r["monthly_used"] == 530 and r["monthly_period"] == "2026-06"


def test_counter_step_new_month_resets_both():
    existing = {"daily_used": 100, "daily_period": "2026-06-30",
                "monthly_used": 500, "monthly_period": "2026-06"}
    r = bs_counter_step(existing, 30, "2026-07-01", "2026-07")
    assert r["daily_used"] == 30 and r["monthly_used"] == 30
    assert r["daily_period"] == "2026-07-01" and r["monthly_period"] == "2026-07"


def test_diff_blocks_computes_to_block_and_to_unblock():
    desired = {(1, 10), (1, 11), (2, 10)}
    current = {(1, 11), (3, 99)}
    to_block, to_unblock = diff_blocks(desired, current)
    assert to_block == {(1, 10), (2, 10)}
    assert to_unblock == {(3, 99)}


def test_strip_removes_only_blocked_user_ids():
    result = strip_blocked_clients(base(), {2})
    emails = [c["email"] for c in result["inbounds"][0]["settings"]["clients"]]
    assert emails == ["1.alice", "10.carol"]


def test_strip_matches_full_uid_prefix_not_substring():
    # uid=1 must not affect email "10.carol"
    result = strip_blocked_clients(base(), {1})
    emails = [c["email"] for c in result["inbounds"][0]["settings"]["clients"]]
    assert emails == ["2.bob", "10.carol"]


def test_strip_empty_set_returns_same_object():
    cfg = base()
    assert strip_blocked_clients(cfg, set()) is cfg


def test_strip_does_not_mutate_input():
    cfg = base()
    snapshot = copy.deepcopy(dict(cfg))
    strip_blocked_clients(cfg, {1, 2})
    assert dict(cfg) == snapshot


def test_strip_no_mutation_with_shallow_copy_plain_dict():
    # plain dict.copy() поверхностный; функция всё равно не должна мутировать вход
    cfg = {
        "inbounds": [
            {"tag": "VLESS_TCP", "settings": {"clients": [
                {"email": "1.alice"}, {"email": "2.bob"}]}},
        ],
    }
    snapshot = copy.deepcopy(cfg)
    result = strip_blocked_clients(cfg, {1})
    assert cfg == snapshot
    emails = [c["email"] for c in result["inbounds"][0]["settings"]["clients"]]
    assert emails == ["2.bob"]
