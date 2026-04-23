from fastapi import APIRouter, Depends
from typing import List, Optional
from database import get_db

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("")
async def get_logs(db=Depends(get_db)):
    cursor = db.admin_logs.find().sort("timestamp", -1)
    logs = await cursor.to_list(length=100)
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs

async def create_log(action: str, details: str, db):
    import time
    log_entry = {
        "action": action,
        "details": details,
        "timestamp": int(time.time() * 1000)
    }
    await db.admin_logs.insert_one(log_entry)
