import json
import threading
import pika
from prometheus_client import start_http_server
from services.payment_service import PaymentService, TransientError, PermanentError
from repository.mongo_repo import PaymentRepository
from services.payment_service import messages_consumed, payments_successful, payments_failed, retries_total

# ---------------------------
# Setup Repository and Service
# ---------------------------
repo = PaymentRepository()
service = PaymentService(repo)

# ---------------------------
# RabbitMQ connection
# ---------------------------
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host='rabbitmq',
        port=5672,
        credentials=pika.PlainCredentials('guest', 'guest')
    )
)
channel = connection.channel()
channel.queue_declare(queue='payment_initiation', durable=True)
channel.queue_declare(queue='payment_dlq', durable=True)

# ---------------------------
# Consumer Callback
# ---------------------------
def callback(ch, method, properties, body):
    event = json.loads(body)
    messages_consumed.inc()  # increment counter

    try:
        result = service.process_payment(event)
        if result == "SUCCESS":
            payments_successful.inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except TransientError:
        retries_total.inc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    except PermanentError:
        payments_failed.inc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# ---------------------------
# Start Prometheus server
# ---------------------------
def start_metrics_server():
    start_http_server(8001)
    print("Prometheus metrics server running on port 8001")

metrics_thread = threading.Thread(target=start_metrics_server)
metrics_thread.start()

# ---------------------------
# Start consuming
# ---------------------------
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='payment_initiation', on_message_callback=callback)
print(" [*] Waiting for messages...")
channel.start_consuming()
