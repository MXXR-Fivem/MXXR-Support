from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from bot.config.models import AppConfig
from bot.constants.defaults import DEFAULT_CONFIG_PATH, DEFAULT_DATABASE_PATH, DEFAULT_DATA_DIR


class EnvironmentSettings(BaseModel):
    discord_token: str
    discord_client_id: int
    discord_guild_id: int | None = None
    tebex_api_key: str | None = None
    tebex_base_url: str = "https://plugin.tebex.io"
    bot_primary_color: str | None = None
    review_api_host: str = "127.0.0.1"
    review_api_port: int = 8081
    review_api_bearer_token: str | None = None
    review_api_allowed_origins: tuple[str, ...] = ()
    deepl_api_base_url: str = "https://api-free.deepl.com"
    deepl_api_key: str | None = None
    translation_api_base_url: str | None = None
    translation_api_key: str | None = None
    translation_api_model: str | None = None
    environment: str = "development"
    log_level: str = "INFO"
    config_path: Path = DEFAULT_CONFIG_PATH
    database_path: Path = DEFAULT_DATABASE_PATH
    data_dir: Path = DEFAULT_DATA_DIR


class ApiEnvironmentSettings(BaseModel):
    review_api_host: str = "127.0.0.1"
    review_api_port: int = 8081
    review_api_bearer_token: str | None = None
    review_api_allowed_origins: tuple[str, ...] = ()
    log_level: str = "INFO"
    environment: str = "development"
    database_path: Path = DEFAULT_DATABASE_PATH
    data_dir: Path = DEFAULT_DATA_DIR


def load_environment(dotenv_path: str | Path = ".env") -> EnvironmentSettings:
    """Load environment variables from disk and validate the bot runtime settings.

    ## Parameters
        - dotenv_path: Path to the environment file to load before validation.

    ## Returns
        A validated EnvironmentSettings instance.
    """

    load_dotenv(dotenv_path=dotenv_path)
    return EnvironmentSettings(
        discord_token=os.environ["DISCORD_TOKEN"],
        discord_client_id=int(os.environ["DISCORD_CLIENT_ID"]),
        discord_guild_id=_read_optional_int("DISCORD_GUILD_ID"),
        tebex_api_key=os.getenv("TEBEX_API_KEY"),
        tebex_base_url=os.getenv("TEBEX_BASE_URL", "https://plugin.tebex.io"),
        bot_primary_color=os.getenv("BOT_PRIMARY_COLOR"),
        review_api_host=os.getenv("REVIEW_API_HOST", "127.0.0.1"),
        review_api_port=int(os.getenv("REVIEW_API_PORT", "8081")),
        review_api_bearer_token=os.getenv("REVIEW_API_BEARER_TOKEN"),
        review_api_allowed_origins=_read_optional_csv("REVIEW_API_ALLOWED_ORIGINS"),
        deepl_api_base_url=os.getenv("DEEPL_API_BASE_URL", "https://api-free.deepl.com"),
        deepl_api_key=os.getenv("DEEPL_API_KEY"),
        translation_api_base_url=os.getenv("TRANSLATION_API_BASE_URL"),
        translation_api_key=os.getenv("TRANSLATION_API_KEY"),
        translation_api_model=os.getenv("TRANSLATION_API_MODEL"),
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        config_path=Path(os.getenv("CONFIG_PATH", str(DEFAULT_CONFIG_PATH))),
        database_path=Path(os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))),
        data_dir=Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR))),
    )


def load_api_environment(dotenv_path: str | Path = ".env") -> ApiEnvironmentSettings:
    """Load only the runtime settings required by the standalone review API."""

    load_dotenv(dotenv_path=dotenv_path)
    return ApiEnvironmentSettings(
        review_api_host=os.getenv("REVIEW_API_HOST", "127.0.0.1"),
        review_api_port=int(os.getenv("REVIEW_API_PORT", "8081")),
        review_api_bearer_token=os.getenv("REVIEW_API_BEARER_TOKEN"),
        review_api_allowed_origins=_read_optional_csv("REVIEW_API_ALLOWED_ORIGINS"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        environment=os.getenv("ENVIRONMENT", "development"),
        database_path=Path(os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))),
        data_dir=Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR))),
    )


def load_app_config(config_path: str | Path) -> AppConfig:
    """Load and validate the YAML application configuration file.

    ## Parameters
        - config_path: YAML file path containing functional application configuration.

    ## Returns
        A validated AppConfig instance.
    """

    with Path(config_path).open("r", encoding="utf-8") as handle:
        raw_config = yaml.safe_load(handle) or {}
    return AppConfig.model_validate(raw_config)


def _read_optional_int(name: str) -> int | None:
    """Read an optional integer environment variable when it is defined.

    ## Parameters
        - name: Environment variable name to parse as an integer when present.

    ## Returns
        The parsed integer or None.
    """

    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return None
    return int(raw_value)


def _read_optional_csv(name: str) -> tuple[str, ...]:
    """Read a comma-separated environment variable and return normalized items."""

    raw_value = os.getenv(name, "")
    values = [item.strip() for item in raw_value.split(",")]
    return tuple(item for item in values if item)
