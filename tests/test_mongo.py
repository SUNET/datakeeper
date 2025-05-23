from pymongo import MongoClient
# mongo_url: mongodb://mongo_admin_db:xU84ASGk9A==@public-dco-test-mongodb-1.streams.sunet.se:27017, mongo_db: aisdb, mongo_collection: vessels
# 
# client = MongoClient("mongodb://mongoadmin:f48f8@localhost:27017")
client = MongoClient("mongodb://mongo_admin_db:xU84ASGk9A==@public-dco-test-mongodb-1.streams.sunet.se:27017")
try:
    client.admin.command('ping')
    print("✅ MongoDB connected successfully.")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
