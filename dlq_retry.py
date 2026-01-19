import pika
import json
import time
import os

# ---------------- RabbitMQ ----------------
MQ_HOST = os.getenv("MQ_HOST", "rabbitmq")
MQ_PORT = int(os.getenv("MQ_PORT", 5672))
MQ_USER = os.getenv("MQ_USER", "guest")
MQ_PASS = os.getenv("MQ_PASS", "guest")
QUEUE = os.getenv("PAYMENT_INITIATION_QUEUE", "payment_initiation")
DLQ = os.getenv("PAYMENT_DLQ", "payment_dlq")
RETRY_DELAY = int(os.getenv("DLQ_RETRY_DELAY_SECONDS", 10))  # Delay before retry

credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=MQ_HOST, port=MQ_PORT, credentials=credentials)
)
channel = connection.channel()
channel.queue_declare(queue=QUEUE, durable=True)
channel.queue_declare(queue=DLQ, durable=True)

# ---------------- DLQ Consumer ----------------
def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        print("Invalid message in DLQ, skipping")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Check if this was a transient failure
    metadata = event.get("metadata", {})
    if metadata.get("simulate_transient_failure", False):
        print(f"[~] Retrying transient failure: {event['idempotency_key']} after {RETRY_DELAY}s")
        time.sleep(RETRY_DELAY)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE,
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,
                headers={"x-retry-count": 0}  # reset retry count
            )
        )
    else:
        print(f"[X] Permanent failure, leaving in DLQ: {event['idempotency_key']}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=DLQ, on_message_callback=callback)
print(f"[*] Listening to DLQ: {DLQ} for retries...")
channel.start_consuming()
