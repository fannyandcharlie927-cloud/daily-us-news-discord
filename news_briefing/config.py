from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str | None
    openai_api_key: str | None
    openai_model: str
    max_articles: int
    local_timezone: ZoneInfo
    dry_run: bool


def load_settings(dry_run: bool = False) -> Settings:
    timezone_name = os.getenv("LOCAL_TIMEZONE", "Australia/Hobart")
    return Settings(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_articles=int(os.getenv("MAX_ARTICLES", "5")),
        local_timezone=ZoneInfo(timezone_name),
        dry_run=dry_run,
    )
