"""
ConvoYield Cloud — Webhook Delivery.

Fires HTTP POST webhooks to registered URLs when yield events match triggers.
Uses stdlib urllib — no new dependencies.

Triggers:
    high_yield  — estimated_yield >= webhook threshold
    high_risk   — risk_level >= 0.7
    arbitrage   — any arbitrage types detected
    all         — fires on every event
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger(__name__)


def check_and_fire_webhooks(db, account_id: str, event_data: dict):
    """Match an event against registered webhooks and deliver matches."""
    webhooks = db.get_active_webhooks(account_id)
    if not webhooks:
        return

    for wh in webhooks:
        events = json.loads(wh.get("events", "[]"))
        threshold = wh.get("threshold", 100.0)
        url = wh.get("url", "")
        if not url:
            continue

        should_fire = False

        if "all" in events:
            should_fire = True
        if "high_yield" in events and event_data.get("estimated_yield", 0) >= threshold:
            should_fire = True
        if "high_risk" in events and event_data.get("risk_level", 0) >= 0.7:
            should_fire = True
        if "arbitrage" in events and event_data.get("arbitrage_types", "[]") != "[]":
            arb = event_data.get("arbitrage_types", "[]")
            parsed = json.loads(arb) if isinstance(arb, str) else arb
            if parsed:
                should_fire = True

        if should_fire:
            payload = {
                "event": "yield_event",
                "account_id": account_id,
                "data": event_data,
                "timestamp": datetime.utcnow().isoformat(),
                "webhook_id": wh.get("id", ""),
            }
            _deliver_webhook(url, payload, retries=1)


def _deliver_webhook(url: str, payload: dict, retries: int = 1):
    """HTTP POST a JSON payload to a URL with optional retry."""
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ConvoYield-Webhook/1.0",
    }

    for attempt in range(1 + retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    logger.info("Webhook delivered to %s (status %d)", url, resp.status)
                    return
                logger.warning("Webhook to %s returned status %d", url, resp.status)
        except (urllib.error.URLError, OSError) as e:
            logger.warning("Webhook delivery attempt %d to %s failed: %s", attempt + 1, url, e)

    logger.error("Webhook delivery to %s failed after %d attempts", url, 1 + retries)
