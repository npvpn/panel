from app.subscription.custom_headers import parse_custom_headers


def test_empty_returns_empty_dict():
    assert parse_custom_headers("") == {}
    assert parse_custom_headers("   ") == {}


def test_single_routing_enable():
    assert parse_custom_headers("routing-enable: 0") == {"routing-enable": "0"}


def test_multiple_lines_blanks_and_comments_skipped():
    raw = "routing-enable: 0\n\n# comment\nX-Test: hello\n"
    assert parse_custom_headers(raw) == {
        "routing-enable": "0",
        "X-Test": "hello",
    }


def test_value_with_colon_splits_on_first_only():
    assert parse_custom_headers("X-Url: https://example.com/x") == {
        "X-Url": "https://example.com/x"
    }


def test_line_without_colon_skipped():
    assert parse_custom_headers("garbage line") == {}


def test_invalid_header_name_skipped():
    # пробел в имени — не RFC-token
    assert parse_custom_headers("Bad Header: x") == {}


def test_control_char_in_value_skipped():
    assert parse_custom_headers("X-Test: a\x00b") == {}


def test_duplicate_name_last_wins():
    assert parse_custom_headers("X-A: 1\nX-A: 2") == {"X-A": "2"}
