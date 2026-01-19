import json
import time
import pika
from config import Config
from services.payment_service import TransientError, PermanentError


class MQConsumer:
    def __init__(self, payment_service):
        self.payment_service = payment_service
        self.channel = None
        self._connect_to_rabbitmq()

    def _connect_to_rabbitmq(self):
        """Retry connection until RabbitMQ is ready"""
        while True:
            try:
                print("Connecting to RabbitMQ...")
                credentials = pika.PlainCredentials(
                    Config.MQ_USER, Config.MQ_PASS
                )

                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=Config.MQ_HOST,
                        port=Config.MQ_PORT,
                        credentials=credentials,
                        heartbeat=600,
                        blocked_connection_timeout=300
                    )
                )

                self.channel = connection.channel()

                self.channel.queue_declare(
                    queue=Config.PAYMENT_INITIATION_QUEUE,
                    durable=True
                )
                self.channel.queue_declare(
                    queue=Config.PAYMENT_DLQ,
                    durable=True
                )

                print("Connected to RabbitMQ ✅")
                break

            except pika.exceptions.AMQPConnectionError:
                print("RabbitMQ not ready, retrying in 5 seconds...")
                time.sleep(5)

    def start(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=Config.PAYMENT_INITIATION_QUEUE,
            on_message_callback=self._callback
        )
        print("Waiting for payment messages...")
        self.channel.start_consuming()

    def _callback(self, ch, method, properties, body):
        event = json.loads(body)

        try:
            self.payment_service.process_payment(event)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except TransientError as e:
            retries = 0
            if properties.headers and "x-retry" in properties.headers:
                retries = properties.headers["x-retry"]

            print(f"Transient error, retry {retries}: {str(e)}")

            if retries >= Config.PAYMENT_RETRY_LIMIT:
                print("Retry limit exceeded, sending to DLQ ❌")
                ch.basic_publish(
                    exchange="",
                    routing_key=Config.PAYMENT_DLQ,
                    body=body
                )
            else:
                delay = 2 ** retries
                time.sleep(delay)

                ch.basic_publish(
                    exchange="",
                    routing_key=Config.PAYMENT_INITIATION_QUEUE,
                    body=body,
                    properties=pika.BasicProperties(
                        headers={"x-retry": retries + 1},
                        delivery_mode=2
                    )
                )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except PermanentError as e:
            print(f"Permanent error, sending to DLQ ❌: {str(e)}")
            ch.basic_publish(
                exchange="",
                routing_key=Config.PAYMENT_DLQ,
                body=body
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
