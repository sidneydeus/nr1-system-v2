import os
import httpx
import logging

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def notify_scheduling_webhook(event_type: str, payload: dict) -> bool:
    """Fire-and-forget webhook for scheduling events. Non-blocking, 5s timeout."""
    if not WEBHOOK_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(WEBHOOK_URL, json={"event": event_type, **payload})
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(f"Webhook failed: {e}")
        return False
