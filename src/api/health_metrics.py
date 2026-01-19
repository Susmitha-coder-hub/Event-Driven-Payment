from flask import Flask, Response, jsonify
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import pika
import pymongo
import os

app = Flask(__name__)

# ---------- PROMETHEUS METRICS ----------

messages_consumed = Counter(
    "payment_processor_messages_consumed_total",
    "Total payment messages consumed"
)

payments_successful = Counter(
    "payment_processor_payments_successful_total",
    "Total successful payments"
)

payments_failed = Counter(
    "payment_processor_payments_failed_total",
    "Total permanently failed payments (DLQ)"
)

payment_retries = Counter(
    "payment_processor_retries_total",
    "Total payment retries"
)

# ---------- HEALTH CHECK ----------

@app.route("/health", methods=["GET"])
def health():
    try:
        # Check MongoDB
        mongo_client = pymongo.MongoClient(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            serverSelectionTimeoutMS=2000
        )
        mongo_client.admin.command("ping")

        # Check RabbitMQ
        credentials = pika.PlainCredentials(
            os.getenv("MQ_USER"), os.getenv("MQ_PASS")
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.getenv("MQ_HOST"),
                port=int(os.getenv("MQ_PORT")),
                credentials=credentials,
                blocked_connection_timeout=2
            )
        )
        connection.close()

        return jsonify({"status": "healthy"}), 200

    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


# ---------- METRICS ----------

@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
