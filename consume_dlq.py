import pika, json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='payment_dlq', durable=True)

def callback(ch, method, properties, body):
    print("DLQ Message:", json.loads(body))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='payment_dlq', on_message_callback=callback)
print("Waiting for DLQ messages...")
channel.start_consuming()
