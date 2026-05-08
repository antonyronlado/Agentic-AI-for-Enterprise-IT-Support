from fastapi import APIRouter, Depends
from typing import Optional
from database import get_db
import time

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
async def get_logs(
    limit: int = 100,
    ticket_id: Optional[str] = None,
    db=Depends(get_db),
):
    query = {"ticket_id": ticket_id} if ticket_id else {}
    cursor = db.admin_logs.find(query).sort("timestamp", -1)
    logs = await cursor.to_list(length=limit)
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs


async def create_log(
    action: str,
    details: str,
    db,
    agent: str = "system",
    ticket_id: Optional[str] = None,
):
    entry = {
        "action":    action,
        "agent":     agent,
        "ticket_id": ticket_id,
        "details":   details,
        "timestamp": int(time.time() * 1000),
    }
    await db.admin_logs.insert_one(entry)
