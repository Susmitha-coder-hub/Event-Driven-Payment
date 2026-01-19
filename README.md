# Event-Driven-Payment
A robust, event-driven backend service that reliably processes **PaymentInitiated** events from a message queue (RabbitMQ), 
ensures exactly-once semantics using idempotency keys, handles transient failures with retries (exponential backoff), 
routes permanently failed messages to a Dead-Letter Queue (DLQ), and persists transaction state in MongoDB.

Designed with fault-tolerance, observability, and horizontal scalability in mind — ideal for high-stakes domains like e-commerce and fintech.

## Features

- **Idempotent processing** using unique `idempotency_key`
- **Retry mechanism** with exponential backoff for transient failures
- **Dead-Letter Queue** for messages that exhaust retries or fail permanently
- **Transactional integrity** via MongoDB
- **Health check** endpoint (`/health`)
- **Prometheus-compatible metrics** endpoint (`/metrics`)
- Fully containerized setup with **Docker + Docker Compose**
- Unit & integration tests (aiming for high coverage on critical paths)

## Architecture Overview
Publisher
↓
RabbitMQ (payment_initiation queue)
↓
┌───────────────────────────────┐
│     Payment Processor         │
│   (multiple instances possible)│
│                               │
│  • Message consumer           │
│  • Idempotency check          │
│  • Retry logic                │
│  • DLQ routing                │
└───────────────┬───────────────┘
│
MongoDB (payment_transactions)
│
┌──────────┴──────────┐
│                     │
/health               /metrics (Prometheus)
text**Key design decisions:**

- **Idempotency**: Unique key + database constraint prevents duplicate processing even under concurrent consumers or message re-deliveries.
- **Retry strategy**: Basic exponential backoff with sleep (for simplicity). In production, prefer RabbitMQ retry queues with TTL + dead-lettering.
- **Error classification**: Transient errors (network, timeouts) → retry; Permanent errors (validation, business rules) → immediate DLQ.
- **Exactly-once semantics**: Achieved via idempotency + manual ack/nack (at-least-once delivery + deduplication).
- **Observability**: Structured logging + Prometheus metrics + health endpoint.

## Prerequisites

- Docker 20+  
- Docker Compose 1.29+  
- Git

## Quick Start

1. Clone the repository

```bash
git clone https://github.com/<your-username>/payment-processor.git
cd payment-processor

Copy and review environment variables

Bashcp .env.example .env
# Usually no changes needed for local development

Start all services

Bashdocker compose build
docker compose up -d

Check that everything is healthy

Bash# Should return {"status": "healthy"}
curl http://localhost:8000/health

# View Prometheus metrics
curl http://localhost:8000/metrics

# See RabbitMQ management UI (user: guest, pass: guest)
# http://localhost:15672

View logs

Bashdocker compose logs -f payment-processor
How to Publish Test Payment Events
A simple publisher script is included (publisher.py).
Bash# Install pika locally if needed
pip install pika

python publisher.py
Or run individual examples:
Python# Inside python shell or new file
from publisher import publish_payment_event

publish_payment_event(99.99, "USD", "user_123", idempotency_key="test-abc-001")
publish_payment_event(49.50, "EUR", "user_456", idempotency_key="test-abc-001")  # should be ignored (idempotent)
publish_payment_event(150.00, "USD", "user_789", simulate_transient_failure=True)  # will retry
Monitoring & Debugging

RabbitMQ Management: http://localhost:15672
→ Check queue lengths, move messages manually, inspect DLQ
MongoDB (optional mongo client / compass / mongosh):

Bashdocker exec -it payment-processor-mongodb-1 mongosh -u root -p rootpassword
use payment_db
db.payment_transactions.find().pretty()

Metrics endpoint (Prometheus format):

textpayment_processor_messages_consumed_total 12
payment_processor_payments_successful_total 9
payment_processor_payments_failed_total 1
payment_processor_retries_total 4
Running Tests
Unit tests (fast, no dependencies):
Bashpytest tests/unit/ -v
Integration / end-to-end tests (requires docker compose running):
Bash# Make sure services are up
docker compose up -d

pytest tests/integration/ -v
Project Structure
textpayment-processor/
├── src/
│   ├── main.py                     # Starts consumer + HTTP server
│   ├── config.py
│   ├── services/
│   │   ├── payment_service.py      # Business logic + idempotency
│   │   └── message_queue_consumer.py
│   ├── models/
│   │   └── payment_model.py        # MongoDB schema & operations
│   └── api/
│       └── health_metrics.py       # /health & /metrics endpoints
├── tests/
│   ├── unit/
│   └── integration/
├── publisher.py                    # Helper script to send test messages
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
Environment Variables (.env)
All sensitive / configurable values are controlled via environment variables.
See .env.example for the full list and default values.
Production Considerations (Next Steps)

Use separate retry queues with TTL + dead-lettering instead of sleep-based backoff
Add distributed tracing (OpenTelemetry / Jaeger)
Rate limiting & circuit breakers for external payment gateways
Use PostgreSQL instead of MongoDB if strong consistency is critical
Add authentication to management endpoints
Deploy with Kubernetes / ECS + autoscaling based on queue length
Add alerting on DLQ message count

License
MIT

Built as a learning / portfolio project demonstrating event-driven architecture, fault tolerance, and production-ready patterns.
