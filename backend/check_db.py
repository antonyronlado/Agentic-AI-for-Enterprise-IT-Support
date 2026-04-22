import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017/agentic_ai")
    db = client.get_default_database("agentic_ai")
    cursor = db.tickets.find({})
    tickets = await cursor.to_list(length=100)
    for t in tickets:
        print(f"ID: {t['_id']} | Status: {t['status']} | Title: {t['title']}")
        if "resolution" in t:
            print(f"  Resolution: {t['resolution']['result']}")
        else:
            print("  No resolution attached.")

if __name__ == "__main__":
    asyncio.run(check_db())
