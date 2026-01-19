from threading import Thread
from config import Config
from models.payment_model import PaymentRepository
from services.payment_service import PaymentService
from services.message_queue_consumer import MQConsumer
from api.health_metrics import app


def start_consumer():
    repo = PaymentRepository(Config)
    service = PaymentService(repo)
    consumer = MQConsumer(service)
    consumer.start()


if __name__ == "__main__":
    Thread(target=start_consumer, daemon=True).start()
    app.run(host="0.0.0.0", port=Config.SERVICE_PORT)
