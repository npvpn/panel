from app.xray.cascade_keys import generate_cascade_identity


def test_identity_uses_injected_uuid():
    assert generate_cascade_identity(uuid_str="u-1") == {"uuid": "u-1"}


def test_identity_autogenerates_unique_uuid():
    a = generate_cascade_identity()
    b = generate_cascade_identity()
    assert a["uuid"] != b["uuid"]
    assert set(a.keys()) == {"uuid"}
