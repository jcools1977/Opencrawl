"""
ConvoYield Cloud — Transactional Email Service.

Uses Resend for delivery. Fails silently if RESEND_API_KEY is not set,
so the platform works without email in dev/test environments.

Env vars:
    RESEND_API_KEY — Resend API key
    FROM_EMAIL     — Sender address (default: ConvoYield <noreply@convoyield.com>)
"""

from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "ConvoYield <noreply@convoyield.com>")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def _send(to: str, subject: str, html: str):
    """Send an email via Resend. No-op if API key is missing."""
    if not RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — skipping email to %s", to)
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
    except Exception as e:
        logger.warning("Failed to send email to %s: %s", to, e)


def send_welcome(email: str, api_key: str, tier: str):
    """Welcome email with API key after registration."""
    _send(
        to=email,
        subject="Welcome to ConvoYield — Your API Key",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#f1f5f9;background:#0a0e17;padding:40px;border-radius:12px;">
            <h1 style="color:#10b981;">Welcome to ConvoYield</h1>
            <p>Your account is ready. Here's your API key:</p>
            <div style="background:#1a2332;padding:16px;border-radius:8px;font-family:monospace;word-break:break-all;color:#06b6d4;">
                {api_key}
            </div>
            <p style="margin-top:16px;"><strong>Tier:</strong> {tier.title()}</p>
            <p>Get started:</p>
            <pre style="background:#1a2332;padding:16px;border-radius:8px;color:#94a3b8;overflow-x:auto;">
curl -X POST {BASE_URL}/api/v1/events/yield \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"session_id":"test","turn_number":1,...}}'</pre>
            <p><a href="{BASE_URL}/dashboard" style="color:#10b981;">Open Dashboard</a></p>
        </div>
        """,
    )


def send_subscription_receipt(email: str, product_id: str, product_type: str):
    """Payment receipt after successful checkout."""
    label = product_id.replace("_", " ").title()
    kind = "plan upgrade" if product_type == "tier" else "playbook subscription"
    _send(
        to=email,
        subject=f"ConvoYield — {label} Activated",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#f1f5f9;background:#0a0e17;padding:40px;border-radius:12px;">
            <h1 style="color:#10b981;">Payment Confirmed</h1>
            <p>Your {kind} is now active:</p>
            <div style="background:#1a2332;padding:16px;border-radius:8px;">
                <strong style="color:#06b6d4;">{label}</strong>
            </div>
            <p style="margin-top:16px;">
                <a href="{BASE_URL}/dashboard" style="color:#10b981;">Go to Dashboard</a>
            </p>
        </div>
        """,
    )


def send_cancellation_notice(email: str, product_id: str):
    """Downgrade/cancellation notice."""
    label = product_id.replace("_", " ").title()
    _send(
        to=email,
        subject=f"ConvoYield — {label} Canceled",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#f1f5f9;background:#0a0e17;padding:40px;border-radius:12px;">
            <h1 style="color:#f59e0b;">Subscription Canceled</h1>
            <p>Your <strong>{label}</strong> subscription has been canceled.</p>
            <p>You've been moved to the free tier. Your data will be retained for 7 days.</p>
            <p>Changed your mind? <a href="{BASE_URL}/#pricing" style="color:#10b981;">Resubscribe anytime</a>.</p>
        </div>
        """,
    )


def send_high_yield_alert(email: str, session_id: str, yield_value: float):
    """Alert when a session exceeds the yield threshold."""
    _send(
        to=email,
        subject=f"ConvoYield — High Yield Alert: ${yield_value:.2f}",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#f1f5f9;background:#0a0e17;padding:40px;border-radius:12px;">
            <h1 style="color:#10b981;">High Yield Detected</h1>
            <p>Session <code style="color:#06b6d4;">{session_id}</code> has reached:</p>
            <div style="background:#1a2332;padding:16px;border-radius:8px;text-align:center;">
                <span style="font-size:36px;font-weight:800;color:#10b981;">${yield_value:.2f}</span>
                <br><span style="color:#94a3b8;">estimated yield</span>
            </div>
            <p style="margin-top:16px;">
                <a href="{BASE_URL}/dashboard" style="color:#10b981;">View in Dashboard</a>
            </p>
        </div>
        """,
    )
