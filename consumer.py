import os
import sys
import json
import threading
import time
import logging
import pika
from prometheus_client import start_http_server
from flask import Flask, jsonify

# ---------------- PATH FIX ----------------
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from metrics import messages_consumed, payments_successful, payments_failed, retries_total
from services.payment_service import PaymentService, TransientError, PermanentError
from repository.mongo_repo import PaymentRepository

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ---------------- Metrics Server ----------------
def start_metrics():
    port = int(os.getenv("SERVICE_PORT_METRICS", 8001))
    start_http_server(port)
    logging.info(f"Prometheus metrics running on :{port}")

threading.Thread(target=start_metrics, daemon=True).start()

# ---------------- Health Endpoint ----------------
app = Flask(__name__)
@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

# NOTE: Removed the Flask thread start line
# Health endpoint will be served via Gunicorn in production

# ---------------- Repository & Service ----------------
repo = PaymentRepository()
service = PaymentService(repo)

# Ensure unique index on idempotency_key
repo.collection.create_index("idempotency_key", unique=True)

# ---------------- RabbitMQ ----------------
MQ_HOST = os.getenv("MQ_HOST", "rabbitmq")
MQ_PORT = int(os.getenv("MQ_PORT", 5672))
MQ_USER = os.getenv("MQ_USER", "guest")
MQ_PASS = os.getenv("MQ_PASS", "guest")
QUEUE = os.getenv("PAYMENT_INITIATION_QUEUE", "payment_initiation")
DLQ = os.getenv("PAYMENT_DLQ", "payment_dlq")
MAX_RETRIES = int(os.getenv("PAYMENT_RETRY_LIMIT", 3))
INITIAL_DELAY = int(os.getenv("PAYMENT_RETRY_INITIAL_DELAY_SECONDS", 2))

credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=MQ_HOST, port=MQ_PORT, credentials=credentials)
)
channel = connection.channel()
channel.queue_declare(queue=QUEUE, durable=True)
channel.queue_declare(queue=DLQ, durable=True)

# ---------------- Helper ----------------
def backoff(retry):
    return INITIAL_DELAY * (2 ** retry)

# ---------------- Consumer Callback ----------------
def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        logging.error("Failed to decode message, sending to DLQ")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        channel.basic_publish(
            exchange="",
            routing_key=DLQ,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        return

    messages_consumed.inc()
    retry_count = properties.headers.get("x-retry-count", 0) if properties.headers else 0

    try:
        service.process_payment(event)
        payments_successful.inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logging.info(f"[✓] Processed payment | key={event['idempotency_key']}")

    except TransientError:
        retries_total.inc()
        if retry_count < MAX_RETRIES:
            delay = backoff(retry_count)
            logging.warning(f"[~] Retry {event['idempotency_key']} in {delay}s")
            time.sleep(delay)
            channel.basic_publish(
                exchange="",
                routing_key=QUEUE,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={"x-retry-count": retry_count + 1}
                )
            )
        else:
            payments_failed.inc()
            logging.error(f"[X] Max retries reached, sending to DLQ | key={event['idempotency_key']}")
            channel.basic_publish(
                exchange="",
                routing_key=DLQ,
                body=json.dumps(event),
                properties=pika.BasicProperties(delivery_mode=2)
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except PermanentError:
        payments_failed.inc()
        logging.error(f"[X] Permanent failure, sending to DLQ | key={event['idempotency_key']}")
        channel.basic_publish(
            exchange="",
            routing_key=DLQ,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logging.exception(f"[!] Unexpected error for key={event.get('idempotency_key', 'unknown')}: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        channel.basic_publish(
            exchange="",
            routing_key=DLQ,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )

# ---------------- Start Consuming ----------------
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=QUEUE, on_message_callback=callback)
logging.info(f"[*] Waiting for messages on queue: {QUEUE}")
channel.start_consuming()
