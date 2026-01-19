# Dockerfile (consumer)
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Run both consumer and health endpoint via a shell script
CMD ["sh", "-c", "python3 consumer.py & gunicorn -w 2 -b 0.0.0.0:${SERVICE_PORT} consumer:app"]
