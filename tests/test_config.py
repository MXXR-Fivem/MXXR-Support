from pathlib import Path

from bot.config.settings import load_api_environment, load_app_config


def test_example_config_loads() -> None:
    config = load_app_config(Path("config.example.yaml"))
    assert config.branding.shop_name == "MXXR Store"
    assert config.polls.max_options == 5


def test_load_api_environment_without_discord_variables(monkeypatch) -> None:
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)
    monkeypatch.setenv("REVIEW_API_HOST", "0.0.0.0")
    monkeypatch.setenv("REVIEW_API_PORT", "9090")
    monkeypatch.setenv("REVIEW_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("DATABASE_PATH", "data/reviews.sqlite3")

    settings = load_api_environment()

    assert settings.review_api_host == "0.0.0.0"
    assert settings.review_api_port == 9090
    assert settings.review_api_bearer_token == "secret-token"
    assert settings.database_path == Path("data/reviews.sqlite3")
