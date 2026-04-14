from pathlib import Path

from bot.config.settings import load_app_config


def test_example_config_loads() -> None:
    config = load_app_config(Path("config.example.yaml"))
    assert config.branding.shop_name == "MXXR Store"
    assert config.polls.max_options == 5
