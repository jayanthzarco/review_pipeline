"""
Central configuration loader for the Review Pipeline package.

Replaces the old pattern where every module independently did:

    with open(PROJECT_ROOT + "/config.json") as f:
        conf_data = json.load(f)

Settings are loaded once and cached for the process lifetime. Environment
variables take precedence over config.json, so a studio deployment can
override secrets (e.g. via a launcher) without editing the file on disk.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PACKAGE_ROOT, "config.json")


@dataclass(frozen=True)
class Settings:
    ayon_server_url: str
    ayon_api_key: str
    sg_url: str = ""
    sg_script_name: str = ""
    sg_script_key: str = ""
    sg_proxy: str = ""

    @property
    def graphql_url(self) -> str:
        return f"{self.ayon_server_url.rstrip('/')}/graphql"

    @property
    def has_shotgrid(self) -> bool:
        """SG_Playlist review type only makes sense if ShotGrid is configured."""
        return bool(self.sg_url and self.sg_script_name and self.sg_script_key)


def _load_raw_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def get_settings(config_path: str = DEFAULT_CONFIG_PATH) -> Settings:
    """Load + cache Settings. Call reset_settings_cache() to force a reload
    (mainly useful in tests, or if config.json changes mid-session)."""
    raw = _load_raw_config(config_path)

    def resolve(env_key: str, json_key: str) -> str:
        return os.environ.get(env_key) or raw.get(json_key, "") or ""

    settings = Settings(
        ayon_server_url=resolve("AYON_SERVER_URL", "AYON_SERVER_URL"),
        ayon_api_key=resolve("AYON_API_KEY", "AYON_API_KEY"),
        sg_url=resolve("SG_URL", "SG_URL"),
        sg_script_name=resolve("SG_SCRIPT_NAME", "SG_SCRIPT_NAME"),
        sg_script_key=resolve("SG_SCRIPT_KEY", "SG_SCRIPT_KEY"),
        sg_proxy=resolve("SG_PROXY", "SG_PROXY"),
    )

    # ayon_api reads AYON_SERVER_URL / AYON_API_KEY straight from the
    # environment, so make sure it's populated even if the values came
    # from config.json rather than the environment.
    os.environ.setdefault("AYON_SERVER_URL", settings.ayon_server_url)
    os.environ.setdefault("AYON_API_KEY", settings.ayon_api_key)

    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
