import os
import redis
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Add protocol=2 to fix compatibility with Redis v5
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True, #automatically convert Redis binary data into readable text strings.
    protocol=2
)

# MongoDB Connection (Persistent Metadata / Audit logs)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["secret_notes_db"] #database name
audit_collection = db["audit_logs"] #collection name