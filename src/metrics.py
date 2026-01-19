from prometheus_client import Counter, CollectorRegistry

# Custom registry (NOT the global one)
REGISTRY = CollectorRegistry()

messages_consumed = Counter(
    "payment_processor_messages_consumed_total",
    "Total payment messages consumed",
    registry=REGISTRY
)

payments_successful = Counter(
    "payment_processor_payments_successful_total",
    "Total payments successfully processed",
    registry=REGISTRY
)

payments_failed = Counter(
    "payment_processor_payments_failed_total",
    "Total payments permanently failed",
    registry=REGISTRY
)

retries_total = Counter(
    "payment_processor_retries_total",
    "Total retries attempted for transient failures",
    registry=REGISTRY
)
