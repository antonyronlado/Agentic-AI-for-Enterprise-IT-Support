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
    analysis: Optional[Any] = None
    riskAssessment: Optional[Any] = None
    resolution: Optional[Any] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

@router.get("", response_model=List[TicketOut])
async def get_tickets(userId: Optional[str] = None, role: Optional[str] = "user", db=Depends(get_db)):
    if role == "admin":
        # Admin can see all, but filter by userId if specifically requested
        query = {"userId": userId} if userId else {}
    else:
        # Regular user must have userId, if not provided, return none
        if not userId:
            return []
        query = {"userId": userId}

    cursor = db.tickets.find(query).sort("updatedAt", -1)
    tickets = await cursor.to_list(length=100)
    for t in tickets:
        t["_id"] = str(t["_id"])
    return tickets

@router.post("", response_model=TicketOut)
async def create_ticket(ticket: TicketCreate, background_tasks: BackgroundTasks, db=Depends(get_db)):
    from main import _analyzer, _risk_agent, _escalation_agent, _resolver

    now = int(datetime.now().timestamp() * 1000)
    ticket_dict = ticket.model_dump() if hasattr(ticket, "model_dump") else ticket.dict()

    ticket_dict.update({
        "status": "open",
        "priority": "medium",
        "category": "other",
        "createdAt": now,
        "updatedAt": now,
        "history": [{
            "timestamp": now,
            "status": "open",
            "message": "Ticket created by user."
        }]
    })

    new_ticket = await db.tickets.insert_one(ticket_dict)
    created_ticket = await db.tickets.find_one({"_id": new_ticket.inserted_id})

    await db.admin_logs.insert_one({
        "action": "ticket_created",
        "details": f"Ticket '{ticket.title}' created by user '{ticket.userId}'.",
        "timestamp": now
    })

    async def _run_pipeline(ticket_id):
        # Must fetch a fresh DB connection if running in background
        from database import get_db
        bg_db = await get_db()
        
        try:
            # Step 1: NLP Analysis
            analysis = None
            if _analyzer:
                analysis = await _analyzer.run(ticket.title, ticket.description)
                t1 = int(datetime.now().timestamp() * 1000)
                await bg_db.tickets.update_one(
                    {"_id": ticket_id},
                    {"$set": {
                        "status": "analyzing",
                        "priority": analysis.get("suggestedPriority", "medium"),
                        "category": analysis.get("suggestedCategory", "other"),
                        "analysis": analysis,
                        "updatedAt": t1
                    },
                    "$push": {
                        "history": {
                            "timestamp": t1,
                            "status": "analyzing",
                            "message": f"AI analyzed: {analysis.get('intent', 'N/A')}. Confidence: {round(analysis.get('confidenceScore', 0) * 100)}%"
                        }
                    }}
                )

            # Step 2: Risk Assessment
            risk = None
            if _risk_agent:
                priority = analysis.get("suggestedPriority", "medium") if analysis else "medium"
                category = analysis.get("suggestedCategory", "other") if analysis else "other"
                risk = _risk_agent.run(ticket.title, ticket.description, category, priority)
                if _escalation_agent:
                    risk = _escalation_agent.apply(risk)
                t2 = int(datetime.now().timestamp() * 1000)
                await bg_db.tickets.update_one(
                    {"_id": ticket_id},
                    {"$set": {
                        "status": "risk_assessment",
                        "riskAssessment": risk,
                        "updatedAt": t2
                    },
                    "$push": {
                        "history": {
                            "timestamp": t2,
                            "status": "risk_assessment",
                            "message": f"Risk assessed: {risk.get('impact', 'N/A')} impact. Score: {risk.get('riskScore', 'N/A')}. Security: {'Yes' if risk.get('securityRisk') else 'No'}."
                        }
                    }}
                )

            # Step 3: Resolution
            if _resolver:
                resolution = await _resolver.run(ticket.title, ticket.description, analysis, risk)
                final_status = "resolved" if resolution.get("automated") else "resolving"
                t3 = int(datetime.now().timestamp() * 1000)
                await bg_db.tickets.update_one(
                    {"_id": ticket_id},
                    {"$set": {
                        "status": final_status,
                        "resolution": resolution,
                        "updatedAt": t3
                    },
                    "$push": {
                        "history": {
                            "timestamp": t3,
                            "status": final_status,
                            "message": f"{'Auto-resolved via KB' if resolution.get('automated') else 'Resolution path proposed — awaiting agent'}. KB: {resolution.get('kbTitle', 'N/A')}."
                        }
                    }}
                )
        except Exception as e:
            print(f"[Pipeline error] {e}")

    background_tasks.add_task(_run_pipeline, new_ticket.inserted_id)

    if created_ticket:
        created_ticket["_id"] = str(created_ticket["_id"])
    return created_ticket


@router.delete("/{ticket_id}")
async def delete_ticket(ticket_id: str, db=Depends(get_db)):
    result = await db.tickets.delete_one({"_id": ObjectId(ticket_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"message": "Ticket deleted successfully"}

@router.put("/{ticket_id}")
async def update_ticket(ticket_id: str, update_data: dict, db=Depends(get_db)):
    result = await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"message": "Ticket updated successfully"}
