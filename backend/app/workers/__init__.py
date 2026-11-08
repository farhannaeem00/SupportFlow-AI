
import logging
import os
import time

from app.services.webhook_delivery_service import (
    process_due_webhook_deliveries,
)

logger = logging.getLogger("webhook_worker")

POLL_INTERVAL_SECONDS = max(
    5,
    int(os.getenv("WEBHOOK_WORKER_POLL_SECONDS", "10")),
)

BATCH_SIZE = 100


def run_worker() -> None:
    logger.info(
        "Webhook worker started. Poll interval: %s seconds",
        POLL_INTERVAL_SECONDS,
    )

    while True:
        try:
            result = process_due_webhook_deliveries(
                limit=BATCH_SIZE,
            )

            if result["attempted"]:
                logger.info("Webhook batch processed: %s", result)

        except Exception:
            logger.exception("Webhook worker iteration failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_worker()
