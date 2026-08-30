import os
import httpx
import logging

logger = logging.getLogger(__name__)

def get_webhook_url() -> str | None:
    return os.getenv("WEBHOOK_URL")

async def notify_scheduling_webhook(event_type: str, payload: dict) -> bool:
    """Fire-and-forget webhook for scheduling events. Non-blocking, 5s timeout."""
    webhook_url = get_webhook_url()
    if not webhook_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(webhook_url, json={"event": event_type, **payload})
        return True
    except Exception as e:
        logger.warning(f"Webhook failed: {e}")
        return False
