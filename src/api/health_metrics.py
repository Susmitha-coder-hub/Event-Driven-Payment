from flask import Flask, jsonify
from prometheus_client import Counter, generate_latest

app = Flask(__name__)

messages_consumed = Counter(
    "payment_processor_messages_consumed_total",
    "Messages consumed"
)

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/metrics")
def metrics():
    return generate_latest(), 200
