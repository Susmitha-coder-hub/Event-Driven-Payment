import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MQ_HOST = os.getenv("MQ_HOST")
    MQ_PORT = int(os.getenv("MQ_PORT"))
    MQ_USER = os.getenv("MQ_USER")
    MQ_PASS = os.getenv("MQ_PASS")

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT"))
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")

    PAYMENT_INITIATION_QUEUE = os.getenv("PAYMENT_INITIATION_QUEUE")
    PAYMENT_DLQ = os.getenv("PAYMENT_DLQ")

    PAYMENT_RETRY_LIMIT = int(os.getenv("PAYMENT_RETRY_LIMIT"))
    PAYMENT_RETRY_INITIAL_DELAY_SECONDS = int(
        os.getenv("PAYMENT_RETRY_INITIAL_DELAY_SECONDS")
    )

    SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8000))
