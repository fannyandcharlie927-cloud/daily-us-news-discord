from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv

from .collect import collect_articles
from .config import load_settings
from .discord import send_messages
from .formatting import render_report, split_for_discord
from .briefing import build_briefing_items


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Send a verified daily US news briefing to Discord.")
    parser.add_argument("--dry-run", action="store_true", help="Print the report instead of sending to Discord.")
    args = parser.parse_args()

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    settings = load_settings(dry_run=args.dry_run)
    local_now = datetime.now(settings.local_timezone)

    try:
        articles = collect_articles(local_now, settings.max_articles)
        items = build_briefing_items(articles)

        report = render_report(items, local_now, settings.max_articles)
        chunks = split_for_discord(report)

        if settings.dry_run:
            print(report)
            return 0

        if not settings.discord_webhook_url:
            logging.error("DISCORD_WEBHOOK_URL is required unless --dry-run is used.")
            return 2

        send_messages(settings.discord_webhook_url, chunks)
        logging.info("Briefing sent successfully with %s Discord message(s).", len(chunks))
        return 0
    except Exception:
        logging.exception("Daily news briefing failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
