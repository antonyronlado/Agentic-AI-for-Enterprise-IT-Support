import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/agentic_ai")

client = AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database("agentic_ai")

async def get_db():
    return db
