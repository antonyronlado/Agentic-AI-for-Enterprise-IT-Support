import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId

from database import get_db

router = APIRouter(prefix="/tickets", tags=["Tickets"])

MAX_RETRIES = 2


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
    analysis:          Optional[Any] = None
    riskAssessment:    Optional[Any] = None
    resolution:        Optional[Any] = None
    employee_response: Optional[str] = None
    admin_response:    Optional[str] = None
    risk_level:        Optional[str] = None
    confidence_score:  Optional[int] = None
    low_confidence:    Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


_ADMIN_ONLY_FIELDS = {
    "admin_response", "risk_level", "confidence_score",
    "low_confidence", "analysis", "riskAssessment",
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
    from main import _analyzer, _risk_agent, _escalation_agent, _resolver, _kb

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
        "history": [{
            "timestamp": now,
            "status":    "open",
            "message":   "Ticket created. AI pipeline queued.",
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
        _run_full_pipeline,
        new_ticket.inserted_id,
        ticket.title,
        ticket.description,
        _analyzer, _risk_agent, _escalation_agent, _resolver, _kb,
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


async def _run_full_pipeline(
    ticket_id,
    title:       str,
    description: str,
    _analyzer,
    _risk_agent,
    _escalation_agent,
    _resolver,
    _kb,
):
    from database import get_db
    db      = await get_db()
    tid_str = str(ticket_id)

    print(f"[Pipeline] START ticket={tid_str} title='{title}'")

    async def _log(agent: str, action: str, details: str):
        await db.admin_logs.insert_one({
            "action":    action,
            "agent":     agent,
            "ticket_id": tid_str,
            "details":   details,
            "timestamp": int(datetime.now().timestamp() * 1000),
        })

    async def _update(fields: dict, history_msg: str, new_status: str):
        now = int(datetime.now().timestamp() * 1000)
        fields["updatedAt"] = now
        await db.tickets.update_one(
            {"_id": ticket_id},
            {
                "$set":  fields,
                "$push": {
                    "history": {
                        "timestamp": now,
                        "status":    new_status,
                        "message":   history_msg,
                    }
                },
            },
        )

    async def _mark_failed(step: str, reason: str):
        msg = (
            f"[PIPELINE FAILED] Step '{step}' failed after {MAX_RETRIES} "
            f"attempts. Reason: {reason[:200]}"
        )
        print(f"[Pipeline] FAILED at step={step}: {reason}")
        await _log("Pipeline", "pipeline_failed", msg)
        await _update(
            {
                "status":            "failed",
                "employee_response": (
                    "We encountered an issue processing your request automatically. "
                    "Our IT team has been notified and will review your ticket manually. "
                    "We apologise for the inconvenience."
                ),
                "admin_response": f"PIPELINE FAILURE at step: {step}. {reason}",
            },
            msg,
            "failed",
        )

    async def _with_retry(step_name: str, coro_factory):
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await coro_factory()
            except Exception as exc:
                last_exc = exc
                wait = attempt * 2
                print(
                    f"[Pipeline] {step_name} attempt {attempt}/{MAX_RETRIES} "
                    f"failed: {exc}. Retrying in {wait}s..."
                )
                await _log(
                    step_name,
                    f"step_retry_{attempt}",
                    f"Attempt {attempt} failed: {str(exc)[:200]}",
                )
                await asyncio.sleep(wait)
        raise last_exc

    loop = asyncio.get_running_loop()
    await _update({"status": "in_progress"}, "AI pipeline started.", "in_progress")

    analysis = None
    if _analyzer:
        try:
            analysis = await _with_retry(
                "TicketAnalyzer",
                lambda: _analyzer.run(title, description),
            )
            print(f"[Pipeline] TicketAnalyzer OK: category={analysis.get('suggestedCategory')} priority={analysis.get('suggestedPriority')}")
            await _log(
                "TicketAnalyzer", "analysis_complete",
                f"Intent: {analysis.get('intent')} | "
                f"Category: {analysis.get('suggestedCategory')} | "
                f"Priority: {analysis.get('suggestedPriority')} | "
                f"Confidence: {round(analysis.get('confidenceScore', 0) * 100)}%",
            )
            await db.tickets.update_one(
                {"_id": ticket_id},
                {"$set": {
                    "priority": analysis.get("suggestedPriority", "medium"),
                    "category": analysis.get("suggestedCategory", "other"),
                    "analysis": analysis,
                }},
            )
        except Exception as exc:
            await _mark_failed("TicketAnalyzer", str(exc))
            return

    risk = None
    if _risk_agent:
        try:
            _priority = (analysis or {}).get("suggestedPriority", "medium")
            _category = (analysis or {}).get("suggestedCategory", "other")
            risk = await _with_retry(
                "RiskAgent",
                lambda: loop.run_in_executor(
                    None,
                    _risk_agent.run, title, description, _category, _priority,
                ),
            )
            print(f"[Pipeline] RiskAgent OK: level={risk.get('risk_level')} confidence={risk.get('confidence_score')}")
            await _log(
                "RiskAgent", "risk_assessed",
                f"Risk Level: {risk.get('risk_level','?').upper()} | "
                f"Score: {round(risk.get('riskScore', 0) * 100)}% | "
                f"Confidence: {risk.get('confidence_score','?')}% | "
                f"Security: {risk.get('securityRisk', False)}",
            )
        except Exception as exc:
            await _mark_failed("RiskAgent", str(exc))
            return

    if _escalation_agent and risk:
        try:
            risk = await _with_retry(
                "EscalationAgent",
                lambda: loop.run_in_executor(
                    None, _escalation_agent.apply, risk, False,
                ),
            )
            print(f"[Pipeline] EscalationAgent OK: escalate={risk.get('escalate')} final_status={risk.get('final_status')}")
            await _log(
                "EscalationAgent", "escalation_decision",
                f"Escalate: {risk.get('escalate')} | "
                f"LowConf: {risk.get('low_confidence')} | "
                f"Status: {risk.get('final_status','?')}",
            )
        except Exception as exc:
            await _mark_failed("EscalationAgent", str(exc))
            return

    resolution = None
    final_status = "in_progress"

    if _resolver:
        try:
            resolution = await _with_retry(
                "ResolutionAgent",
                lambda: _resolver.run(title, description, analysis, risk),
            )

            print(f"[Pipeline] ResolutionAgent OK: kb={resolution.get('kbTitle')} automated={resolution.get('automated')}")
            print(f"[Pipeline] employee_response length: {len(resolution.get('employee_response') or '')}")
            print(f"[Pipeline] admin_response length:    {len(resolution.get('admin_response') or '')}")

            automated = resolution.get("automated", False)
            if _escalation_agent and risk:
                risk = _escalation_agent.apply(risk, automated=automated)

            final_status     = risk.get("final_status", "in_progress") if risk else "in_progress"
            risk_level       = (risk or {}).get("risk_level", "low")
            confidence_score = (risk or {}).get("confidence_score")
            low_confidence   = (risk or {}).get("low_confidence", False)

            employee_response = resolution.get("employee_response") or ""
            admin_response    = resolution.get("admin_response") or ""

            if not employee_response:
                employee_response = (
                    "Your request is under review by our IT team. "
                    "We will update you shortly."
                )

            await _log(
                "ResolutionAgent", "resolution_generated",
                f"KB: {resolution.get('kbTitle','N/A')} | "
                f"Automated: {automated} | "
                f"FinalStatus: {final_status}",
            )

            await _update(
                {
                    "status":            final_status,
                    "riskAssessment":    risk,
                    "resolution":        resolution,
                    "employee_response": employee_response,
                    "admin_response":    admin_response,
                    "risk_level":        risk_level,
                    "confidence_score":  confidence_score,
                    "low_confidence":    low_confidence,
                },
                (
                    f"Pipeline complete. Status: {final_status.upper()}. "
                    f"Risk: {risk_level.upper()}. "
                    f"{'Auto-resolved.' if automated else 'Awaiting agent.'}"
                    + (" Low AI confidence." if low_confidence else "")
                ),
                final_status,
            )
            print(f"[Pipeline] COMPLETE ticket={tid_str} status={final_status}")

        except Exception as exc:
            await _mark_failed("ResolutionAgent", str(exc))
            return

    try:
        if (
            _kb
            and risk
            and resolution
            and final_status == "resolved"
            and risk.get("risk_level") == "low"
            and resolution.get("steps")
        ):
            _kb.add_resolved_ticket(
                ticket_id=tid_str,
                title=title,
                description=description,
                steps=resolution["steps"],
                result=resolution.get("result", "Resolved via automated pipeline."),
                category=(analysis or {}).get("suggestedCategory", "other"),
            )
            await _log(
                "LearningLoop", "kb_entry_added",
                f"Ticket '{title}' added to knowledge base for future use.",
            )
    except Exception as exc:
        print(f"[LearningLoop] Non-critical error: {exc}")
