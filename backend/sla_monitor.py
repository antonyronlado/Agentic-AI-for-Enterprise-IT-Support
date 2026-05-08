import asyncio

from datetime import datetime


SLA_OPEN_SEC        = 30 * 60
SLA_IN_PROGRESS_SEC = 4 * 60 * 60
CHECK_INTERVAL_SEC  = 5 * 60


async def run_sla_monitor(get_db_func):
    print("[SLA Monitor] Starting — checking every 5 minutes.")
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            await _check_sla(get_db_func)
        except asyncio.CancelledError:
            print("[SLA Monitor] Stopped.")
            break
        except Exception as exc:
            print(f"[SLA Monitor ERROR] {type(exc).__name__}: {exc}")


async def _check_sla(get_db_func):
    db  = await get_db_func()
    now = int(datetime.now().timestamp() * 1000)

    breached: list[dict] = []

    open_deadline = now - (SLA_OPEN_SEC * 1000)
    cursor = db.tickets.find({
        "status": "open",
        "createdAt": {"$lt": open_deadline},
    })
    async for t in cursor:
        breached.append((t, "SLA breach: ticket stayed Open for over 30 minutes without AI processing."))

    progress_deadline = now - (SLA_IN_PROGRESS_SEC * 1000)
    cursor = db.tickets.find({
        "status": "in_progress",
        "updatedAt": {"$lt": progress_deadline},
    })
    async for t in cursor:
        breached.append((t, "SLA breach: ticket has been In Progress for over 4 hours without resolution."))

    if not breached:
        return

    print(f"[SLA Monitor] {len(breached)} SLA breach(es) found — escalating.")

    for ticket, reason in breached:
        tid = ticket["_id"]
        tid_str = str(tid)

        await db.tickets.update_one(
            {"_id": tid},
            {
                "$set": {
                    "status":            "escalated",
                    "updatedAt":         now,
                    "employee_response": (
                        "We noticed your request has been waiting longer than expected. "
                        "It has been escalated to our IT admin team as a priority. "
                        "You will be contacted shortly."
                    ),
                },
                "$push": {
                    "history": {
                        "timestamp": now,
                        "status":    "escalated",
                        "message":   f"[SLA Monitor] Auto-escalated. {reason}",
                    }
                },
            },
        )

        await db.admin_logs.insert_one({
            "action":    "sla_breach_escalated",
            "agent":     "SLAMonitor",
            "ticket_id": tid_str,
            "details":   reason,
            "timestamp": now,
        })

        print(f"[SLA Monitor] Escalated ticket {tid_str}: {reason}")
