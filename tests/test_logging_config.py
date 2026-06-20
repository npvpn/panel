from app.logging_config import LogSettings, build_logging_config


def test_from_env_reads_values_and_defaults():
    s = LogSettings.from_env({"LOG_LEVEL": "DEBUG", "LOG_ACCESS_ENABLED": "false"})
    assert s.level == "DEBUG"
    assert s.access_enabled is False
    assert s.format == "text"  # default


def test_build_config_has_expected_handlers_and_level():
    cfg = build_logging_config(LogSettings(level="WARNING"))
    assert cfg["version"] == 1
    assert "console" in cfg["handlers"]
    assert "file" in cfg["handlers"]
    assert cfg["loggers"]["uvicorn.error"]["level"] == "WARNING"


def test_access_disabled_silences_access_logger():
    cfg = build_logging_config(LogSettings(access_enabled=False))
    assert cfg["loggers"]["uvicorn.access"]["level"] == "CRITICAL"


def test_from_env_parses_noise_paths():
    s = LogSettings.from_env({"LOG_ACCESS_NOISE_PATHS": "/metrics, /healthz"})
    assert s.access_noise_paths == ("/metrics", "/healthz")


def test_build_config_passes_noise_paths_to_filter():
    cfg = build_logging_config(LogSettings(access_noise_paths=("/metrics", "/healthz")))
    assert cfg["filters"]["access_noise"]["noise_paths"] == ["/metrics", "/healthz"]
