from __future__ import annotations

import logging

from nr1_agent.log_store import SQLiteLogStore

logger = logging.getLogger(__name__)


def send_admin_report_alert(
    session_id: str,
    classification: str,
    message: str,
    log_store: SQLiteLogStore,
) -> None:
    """Register an administrative alert for a report that needs risk review.

    This function is the integration point for a future email, webhook, or
    notification provider. For now, the alert is deliberately recorded in the
    application log.
    """
    logger.warning(
        "ADMIN_REPORT_ALERT session_id=%s classification=%s message=%s",
        session_id,
        classification,
        message,
    )
    log_store.save_alert(session_id, classification, message)
