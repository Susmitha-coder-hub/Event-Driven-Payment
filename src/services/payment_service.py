import random
import time
from prometheus_client import Counter

# ---------------------------
# Custom Exceptions
# ---------------------------
class TransientError(Exception):
    """Represents a temporary error that can be retried."""
    pass

class PermanentError(Exception):
    """Represents a permanent error that cannot be retried."""
    pass

# ---------------------------
# Prometheus Counters
# ---------------------------
messages_consumed = Counter(
    'payment_processor_messages_consumed_total',
    'Total payment messages consumed'
)
payments_successful = Counter(
    'payment_processor_payments_successful_total',
    'Total payments successfully processed'
)
payments_failed = Counter(
    'payment_processor_payments_failed_total',
    'Total payments permanently failed'
)
retries_total = Counter(
    'payment_processor_retries_total',
    'Total retries attempted for transient failures'
)

# ---------------------------
# Payment Service
# ---------------------------
class PaymentService:
    def __init__(self, repo):
        """
        repo: repository object to interact with MongoDB.
        Must implement:
          - find_by_idempotency_key(key)
          - create_transaction(transaction_dict)
          - update_transaction(key, update_dict)
        """
        self.repo = repo

    def process_payment(self, event):
        """
        Processes a single payment event.

        Event format:
        {
            "idempotency_key": str,
            "user_id": str,
            "amount": float,
            "currency": str,
            "metadata": {optional dictionary}
        }
        """

        key = event["idempotency_key"]
        messages_consumed.inc()  # Increment total messages consumed

        simulate_transient = event.get("metadata", {}).get("simulate_transient_failure", False)
        simulate_permanent = event.get("metadata", {}).get("simulate_permanent_failure", False)

        # ---------------------------
        # 1️⃣ Idempotency check
        # ---------------------------
        existing = self.repo.find_by_idempotency_key(key)
        if existing and existing["status"] == "COMPLETED":
            return "IDEMPOTENT_SKIP"

        if not existing:
            self.repo.create_transaction({
                "idempotency_key": key,
                "amount": event["amount"],
                "currency": event["currency"],
                "user_id": event["user_id"],
                "status": "PROCESSING",
                "retry_count": 0,
                "last_error_message": None
            })

        # ---------------------------
        # 2️⃣ Payment processing simulation
        # ---------------------------
        try:
            time.sleep(0.1)  # Simulate processing time

            # Simulated failures
            if simulate_transient or random.random() < 0.2:
                raise TransientError("Temporary payment gateway issue")

            if simulate_permanent or random.random() < 0.05:
                raise PermanentError("Invalid card details")

            # ---------------------------
            # 3️⃣ Successful payment
            # ---------------------------
            self.repo.update_transaction(key, {"status": "COMPLETED"})
            payments_successful.inc()
            return "SUCCESS"

        # ---------------------------
        # 4️⃣ Handle transient failures
        # ---------------------------
        except TransientError as e:
            retries_total.inc()

            retry_count = (existing.get("retry_count", 0) + 1) if existing else 1
            self.repo.update_transaction(key, {
                "status": "FAILED",
                "retry_count": retry_count,
                "last_error_message": str(e)
            })

            # Re-raise for consumer to trigger retry logic
            raise

        # ---------------------------
        # 5️⃣ Handle permanent failures
        # ---------------------------
        except PermanentError as e:
            payments_failed.inc()
            self.repo.update_transaction(key, {
                "status": "FAILED",
                "last_error_message": str(e)
            })

            # Re-raise for consumer to send to DLQ
            raise
