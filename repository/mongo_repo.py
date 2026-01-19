import os
from pymongo import MongoClient, ASCENDING
from datetime import datetime

class PaymentRepository:
    def __init__(self):
        host = os.getenv("DB_HOST", "mongodb")
        port = int(os.getenv("DB_PORT", 27017))
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASS", "rootpassword")

        # Connect to MongoDB
        self.client = MongoClient(f"mongodb://{user}:{password}@{host}:{port}/")
        self.db = self.client[os.getenv("DB_NAME", "payment_db")]
        self.collection = self.db["payment_transactions"]

        # Ensure unique index on idempotency_key
        self.collection.create_index(
            [("idempotency_key", ASCENDING)],
            unique=True,
            background=True
        )

    def find_by_idempotency_key(self, key): 
        return self.collection.find_one({"idempotency_key": key})

    def create_transaction(self, transaction):
        transaction["created_at"] = datetime.utcnow()
        transaction["updated_at"] = datetime.utcnow()
        self.collection.insert_one(transaction)

    def update_transaction(self, key, updates):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"idempotency_key": key},
            {"$set": updates}
        )
