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
        "x-test": "hello",
    }


def test_value_with_colon_splits_on_first_only():
    assert parse_custom_headers("X-Url: https://example.com/x") == {
        "x-url": "https://example.com/x"
    }


def test_line_without_colon_skipped():
    assert parse_custom_headers("garbage line") == {}


def test_invalid_header_name_skipped():
    # пробел в имени — не RFC-token
    assert parse_custom_headers("Bad Header: x") == {}


def test_control_char_in_value_skipped():
    assert parse_custom_headers("X-Test: a\x00b") == {}


def test_duplicate_name_last_wins():
    assert parse_custom_headers("X-A: 1\nX-A: 2") == {"x-a": "2"}


def test_non_latin1_value_skipped():
    # кириллица (ord > 255) — отбрасывается
    assert parse_custom_headers("X-Title: Привет") == {}
    # эмодзи (ord > 255) — отбрасывается
    assert parse_custom_headers("X-Title: hello 🎉") == {}


def test_del_char_in_value_skipped():
    assert parse_custom_headers("X-Test: a\x7fb") == {}


def test_latin1_value_kept():
    # é = U+00E9, в Latin-1 → должно сохраниться
    assert parse_custom_headers("X-Note: café") == {"x-note": "café"}


def test_header_name_lowercased():
    assert parse_custom_headers("Routing-Enable: 0") == {"routing-enable": "0"}
    assert parse_custom_headers("Content-Disposition: inline") == {
        "content-disposition": "inline"
    }


def test_starlette_response_single_content_disposition():
    from starlette.responses import Response

    # override: встроенный перетирается кастомным, в raw_headers ровно один
    resp = Response(
        content="x",
        headers={
            "content-disposition": "builtin",
            **parse_custom_headers("Content-Disposition: custom"),
        },
    )
    cd_headers = [
        (name, val)
        for name, val in resp.raw_headers
        if name.lower() == b"content-disposition"
    ]
    assert len(cd_headers) == 1
    assert cd_headers[0][1] == b"custom"


def test_starlette_response_no_crash_on_filtered_non_latin1():
    from starlette.responses import Response

    # кириллица отфильтрована — хедер не попадает, Response не падает
    Response(content="x", headers={**parse_custom_headers("X-Bad: Привет")})
