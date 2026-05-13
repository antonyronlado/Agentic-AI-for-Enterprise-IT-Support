import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId

from database import get_db

router = APIRouter(prefix="/tickets", tags=["Tickets"])


class TicketCreate(BaseModel):
    title: str
    description: str
    userId: str
    userEmail: str


class FeedbackRequest(BaseModel):
    rating: str
    comment: Optional[str] = None


class TicketOut(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    status: str
    priority: str
    category: str
    createdAt: int
    updatedAt: int
    userId: str
    userEmail: str
    history: List[dict]
    analysis:           Optional[Any] = None
    riskAssessment:     Optional[Any] = None
    resolution:         Optional[Any] = None
    employee_response:  Optional[str] = None
    admin_response:     Optional[str] = None
    risk_level:         Optional[str] = None
    confidence_score:   Optional[int] = None
    low_confidence:     Optional[bool] = None
    ai_explanation:     Optional[Any] = None
    confidence_map:     Optional[Any] = None
    duplicate_of:       Optional[str] = None
    affected_users:     Optional[List[str]] = None
    linked_count:       Optional[int] = None
    dedup_confidence:   Optional[float] = None
    master_incident_id: Optional[str] = None
    remediation_action: Optional[Any] = None
    feedback:           Optional[Any] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


_ADMIN_ONLY_FIELDS = {
    "admin_response", "risk_level", "confidence_score", "low_confidence",
    "analysis", "riskAssessment", "ai_explanation", "confidence_map",
    "remediation_action",
}


def _filter_for_role(ticket: dict, role: str) -> dict:
    if role == "admin":
        return ticket
    for field in _ADMIN_ONLY_FIELDS:
        ticket.pop(field, None)
    return ticket


@router.get("", response_model=List[TicketOut])
async def get_tickets(
    userId: Optional[str] = None,
    role:   Optional[str] = "user",
    db=Depends(get_db),
):
    if role == "admin":
        query = {"userId": userId} if userId else {}
    else:
        if not userId:
            return []
        query = {"userId": userId}

    cursor  = db.tickets.find(query).sort("updatedAt", -1)
    tickets = await cursor.to_list(length=100)
    result = []
    for t in tickets:
        t["_id"] = str(t["_id"])
        result.append(_filter_for_role(t, role))
    return result


@router.post("", response_model=TicketOut)
async def create_ticket(
    ticket: TicketCreate,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    from main import _analyzer, _risk_agent, _escalation_agent, _resolver, _kb, _model_loader

    now = int(datetime.now().timestamp() * 1000)
    ticket_dict = ticket.model_dump()
    ticket_dict.update({
        "status":            "open",
        "priority":          "medium",
        "category":          "other",
        "createdAt":         now,
        "updatedAt":         now,
        "employee_response": None,
        "admin_response":    None,
        "risk_level":        None,
        "confidence_score":  None,
        "low_confidence":    None,
        "ai_explanation":    None,
        "confidence_map":    None,
        "duplicate_of":      None,
        "affected_users":    [],
        "linked_count":      0,
        "remediation_action": None,
        "feedback":          None,
        "history": [{
            "timestamp": now,
            "status":    "open",
            "message":   "Ticket created. Agentic workflow queued.",
        }],
    })

    new_ticket = await db.tickets.insert_one(ticket_dict)
    created    = await db.tickets.find_one({"_id": new_ticket.inserted_id})

    await db.admin_logs.insert_one({
        "action":    "ticket_created",
        "agent":     "system",
        "ticket_id": str(new_ticket.inserted_id),
        "details":   f"Ticket '{ticket.title}' created by '{ticket.userId}'.",
        "timestamp": now,
    })

    background_tasks.add_task(
        _run_orchestrated_pipeline,
        new_ticket.inserted_id,
        ticket.title,
        ticket.description,
        _analyzer, _risk_agent, _escalation_agent, _resolver, _kb, _model_loader,
    )

    if created:
        created["_id"] = str(created["_id"])
    return created


@router.delete("/{ticket_id}")
async def delete_ticket(ticket_id: str, db=Depends(get_db)):
    result = await db.tickets.delete_one({"_id": ObjectId(ticket_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"message": "Ticket deleted successfully"}


@router.put("/{ticket_id}")
async def update_ticket(ticket_id: str, update_data: dict, db=Depends(get_db)):
    update_data.pop("_id", None)
    result = await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"message": "Ticket updated successfully"}


@router.post("/{ticket_id}/feedback")
async def submit_feedback(ticket_id: str, req: FeedbackRequest, db=Depends(get_db)):
    if req.rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="rating must be 'positive' or 'negative'")
    try:
        oid = ObjectId(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    now = int(datetime.now().timestamp() * 1000)
    feedback_doc = {"rating": req.rating, "comment": req.comment, "submitted_at": now}

    await db.tickets.update_one({"_id": oid}, {"$set": {"feedback": feedback_doc}})

    ticket = await db.tickets.find_one({"_id": oid}, {"resolution": 1})
    if ticket and ticket.get("resolution", {}).get("retrievedFrom"):
        kb_id = ticket["resolution"]["retrievedFrom"]
        from routers.incidents import router as _
        inc_field = "positive_feedback" if req.rating == "positive" else "negative_feedback"
        await db.kb_articles.update_one(
            {"source_ticket_id": ticket_id},
            {"$inc": {inc_field: 1}},
        )

    await db.admin_logs.insert_one({
        "action":    "feedback_submitted",
        "agent":     "FeedbackLoop",
        "ticket_id": ticket_id,
        "details":   f"User rated resolution as '{req.rating}'. {req.comment or ''}",
        "timestamp": now,
    })

    return {"message": "Feedback recorded. Thank you — this improves future AI accuracy."}


async def _run_orchestrated_pipeline(
    ticket_id, title, description,
    _analyzer, _risk_agent, _escalation_agent, _resolver, _kb, _model_loader,
):
    from database import get_db
    from services.orchestrator import AgentOrchestrator
    db = await get_db()

    orchestrator = AgentOrchestrator(
        analyzer=_analyzer,
        risk_agent=_risk_agent,
        escalation_agent=_escalation_agent,
        resolver=_resolver,
        kb=_kb,
        model_loader=_model_loader,
    )
    await orchestrator.run_pipeline(ticket_id, title, description, db)
