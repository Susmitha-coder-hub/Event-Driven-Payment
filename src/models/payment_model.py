from pymongo import MongoClient, ASCENDING
from datetime import datetime

class PaymentRepository:
    def __init__(self, config):
        uri = f"mongodb://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/admin"
        self.client = MongoClient(uri)
        self.db = self.client[config.DB_NAME]
        self.collection = self.db.payment_transactions

        self.collection.create_index(
            [("idempotency_key", ASCENDING)], unique=True
        )

    def find_by_idempotency_key(self, key):
        return self.collection.find_one({"idempotency_key": key})

    def create_transaction(self, data):
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        self.collection.insert_one(data)

    def update_transaction(self, key, updates):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"idempotency_key": key},
            {"$set": updates}
        )
