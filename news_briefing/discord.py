from __future__ import annotations

import logging
import time

import requests

LOGGER = logging.getLogger(__name__)


def send_messages(webhook_url: str, messages: list[str]) -> None:
    for index, message in enumerate(messages, start=1):
        LOGGER.info("Sending Discord message %s/%s", index, len(messages))
        response = requests.post(webhook_url, json={"content": message}, timeout=20)
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1)
            LOGGER.warning("Discord rate limited request; sleeping %s seconds", retry_after)
            time.sleep(float(retry_after))
            response = requests.post(webhook_url, json={"content": message}, timeout=20)
        response.raise_for_status()
