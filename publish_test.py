import pika
import json
import uuid
from datetime import datetime

# ---------------------------
# 1️⃣ Connect to RabbitMQ
# ---------------------------
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        'localhost',
        5672,
        credentials=pika.PlainCredentials('guest', 'guest')
    )
)
channel = connection.channel()

# Ensure queues exist
channel.queue_declare(queue='payment_initiation', durable=True)

# ---------------------------
# 2️⃣ Function to publish a payment event
# ---------------------------
def publish_payment_event(amount, currency, user_id, idempotency_key=None, simulate_transient_failure=False, simulate_permanent_failure=False):
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    message = {
        "idempotency_key": idempotency_key,
        "amount": amount,
        "currency": currency,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat() + "Z",
        "metadata": {
            "source_system": "test-publisher",
            "simulate_transient_failure": simulate_transient_failure,
            "simulate_permanent_failure": simulate_permanent_failure
        }
    }

    channel.basic_publish(
        exchange='',
        routing_key='payment_initiation',
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)  # persistent
    )
    print(f" [x] Sent payment {idempotency_key} for {amount} {currency} | transient={simulate_transient_failure} | permanent={simulate_permanent_failure}")

# ---------------------------
# 3️⃣ Send test payments
# ---------------------------

# Idempotency test (already tested)
fixed_key = "fixed-key-12345"
publish_payment_event(50.00, "USD", "user-beta", idempotency_key=fixed_key)
publish_payment_event(50.00, "USD", "user-beta", idempotency_key=fixed_key)

# Transient failure test
publish_payment_event(75.00, "USD", "user-gamma", simulate_transient_failure=True)

# Permanent failure test
publish_payment_event(125.00, "USD", "user-delta", simulate_permanent_failure=True)

# ---------------------------
# 4️⃣ Close connection
# ---------------------------
connection.close()
