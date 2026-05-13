from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/automation", tags=["Automation"])


class ApproveRequest(BaseModel):
    approved_by: str = "admin"


@router.get("/actions")
async def list_actions(db=Depends(get_db)):
    actions = []
    async for a in db.remediation_actions.find().sort("created_at", -1).limit(100):
        a["_id"] = str(a["_id"])
        actions.append(a)
    return actions


@router.post("/approve/{action_id}")
async def approve_action(action_id: str, req: ApproveRequest, db=Depends(get_db)):
    try:
        oid = ObjectId(action_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid action ID")

    action = await db.remediation_actions.find_one({"_id": oid})
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Action is in '{action['status']}' state, cannot approve")

    now = int(datetime.now().timestamp() * 1000)
    new_audit = (action.get("audit_trail") or []) + [
        {"event": f"Action approved by {req.approved_by}", "timestamp": now, "actor": "HumanApproval"},
        *[{"event": e, "timestamp": now + (i * 200), "actor": "CARS"} for i, e in enumerate(action.get("audit_events") or [])],
    ]
    await db.remediation_actions.update_one(
        {"_id": oid},
        {"$set": {
            "status": "executed",
            "approved_by": req.approved_by,
            "executed_at": now,
            "updated_at": now,
            "audit_trail": new_audit,
        }}
    )
    await db.admin_logs.insert_one({
        "action": "remediation_approved",
        "agent": "HumanApproval",
        "details": f"Action '{action.get('name')}' approved by {req.approved_by} and executed.",
        "timestamp": now,
    })
    updated = await db.remediation_actions.find_one({"_id": oid})
    if updated:
        updated["_id"] = str(updated["_id"])
    return {"message": f"Action '{action.get('name')}' approved and executed", "action": updated}


@router.post("/reject/{action_id}")
async def reject_action(action_id: str, req: ApproveRequest, db=Depends(get_db)):
    try:
        oid = ObjectId(action_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid action ID")

    action = await db.remediation_actions.find_one({"_id": oid})
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    now = int(datetime.now().timestamp() * 1000)
    new_audit = (action.get("audit_trail") or []) + [
        {"event": f"Action rejected by {req.approved_by}", "timestamp": now, "actor": "HumanApproval"},
    ]
    await db.remediation_actions.update_one(
        {"_id": oid},
        {"$set": {
            "status": "rejected",
            "approved_by": req.approved_by,
            "updated_at": now,
            "audit_trail": new_audit,
        }}
    )
    await db.admin_logs.insert_one({
        "action": "remediation_rejected",
        "agent": "HumanApproval",
        "details": f"Action '{action.get('name')}' rejected by {req.approved_by}.",
        "timestamp": now,
    })
    return {"message": f"Action '{action.get('name')}' rejected"}


@router.post("/rollback/{action_id}")
async def rollback_action(action_id: str, db=Depends(get_db)):
    try:
        oid = ObjectId(action_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid action ID")

    action = await db.remediation_actions.find_one({"_id": oid})
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("status") != "executed":
        raise HTTPException(status_code=409, detail="Only executed actions can be rolled back")

    now = int(datetime.now().timestamp() * 1000)
    await db.remediation_actions.update_one(
        {"_id": oid},
        {"$set": {"status": "rolled_back", "rolled_back": True, "updated_at": now}}
    )
    await db.admin_logs.insert_one({
        "action": "remediation_rollback",
        "agent": "RemediationSystem",
        "details": f"Action '{action.get('name')}' rolled back. Plan: {action.get('rollback_plan', 'N/A')}",
        "timestamp": now,
    })
    return {
        "message": f"Action '{action.get('name')}' rolled back",
        "rollback_plan": action.get("rollback_plan"),
    }
