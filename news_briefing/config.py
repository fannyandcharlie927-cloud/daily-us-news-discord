from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str | None
    max_articles: int
    local_timezone: ZoneInfo
    dry_run: bool


def load_settings(dry_run: bool = False) -> Settings:
    timezone_name = os.getenv("LOCAL_TIMEZONE", "Australia/Hobart")
    return Settings(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        max_articles=int(os.getenv("MAX_ARTICLES", "8")),
        local_timezone=ZoneInfo(timezone_name),
        dry_run=dry_run,
    )
