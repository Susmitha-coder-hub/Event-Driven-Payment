import pika
import json
import uuid
from datetime import datetime

# ---------------------------
# RabbitMQ Configuration
# ---------------------------
MQ_HOST = "localhost"   # for local run
MQ_PORT = 5672
MQ_USER = "guest"
MQ_PASS = "guest"
PAYMENT_QUEUE = "payment_initiation"

# ---------------------------
# Connect to RabbitMQ
# ---------------------------
credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=MQ_HOST,
        port=MQ_PORT,
        credentials=credentials
    )
)

channel = connection.channel()

# Ensure queue exists
channel.queue_declare(queue=PAYMENT_QUEUE, durable=True)

# ---------------------------
# Publish Payment Event
# ---------------------------
def publish_payment_event(
    amount,
    currency,
    user_id,
    idempotency_key=None,
    simulate_transient_failure=False,
    simulate_permanent_failure=False
):
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    event = {
        "idempotency_key": idempotency_key,
        "amount": amount,
        "currency": currency,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {
            "source": "publish_test",
            "simulate_transient_failure": simulate_transient_failure,
            "simulate_permanent_failure": simulate_permanent_failure
        }
    }

    channel.basic_publish(
        exchange="",
        routing_key=PAYMENT_QUEUE,
        body=json.dumps(event),
        properties=pika.BasicProperties(
            delivery_mode=2  # make message persistent
        )
    )

    print(
        f"[x] Sent payment | key={idempotency_key} | "
        f"{amount} {currency} | "
        f"transient={simulate_transient_failure} | "
        f"permanent={simulate_permanent_failure}"
    )

# ---------------------------
# Test Scenarios
# ---------------------------

print("\n--- Sending test payment events ---\n")

# 1️⃣ Idempotency test (same key twice)
fixed_key = "fixed-key-12345"
publish_payment_event(50.0, "USD", "user-alpha", idempotency_key=fixed_key)
publish_payment_event(50.0, "USD", "user-alpha", idempotency_key=fixed_key)

# 2️⃣ Transient failure (should retry)
publish_payment_event(
    75.0,
    "USD",
    "user-beta",
    simulate_transient_failure=True
)

# 3️⃣ Permanent failure (should go to DLQ)
publish_payment_event(
    125.0,
    "USD",
    "user-gamma",
    simulate_permanent_failure=True
)

# ---------------------------
# Close connection
# ---------------------------
connection.close()

print("\n✔ All test messages published\n")
