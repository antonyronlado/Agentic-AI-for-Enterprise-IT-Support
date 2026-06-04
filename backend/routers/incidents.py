from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime

from database import get_db
from auth_deps import require_auth, require_admin

router = APIRouter(prefix="/incidents", tags=["Incidents"])


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_incidents(
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    incidents = []
    async for inc in db.master_incidents.find().sort("created_at", -1):
        incidents.append(_serialize(inc))
    return incidents


@router.post("/cluster")
async def trigger_clustering(
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    from main import _rca_agent
    if not _rca_agent:
        raise HTTPException(status_code=503, detail="RCA agent not initialized")
    clusters = await _rca_agent.cluster_tickets(db)
    return {"clusters_found": len(clusters), "incidents": clusters}


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    try:
        inc = await db.master_incidents.find_one({"_id": ObjectId(incident_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    ticket_ids = inc.get("affected_ticket_ids", [])
    tickets = []
    for tid in ticket_ids:
        try:
            t = await db.tickets.find_one(
                {"_id": ObjectId(tid)},
                {"title": 1, "status": 1, "priority": 1, "userId": 1},
            )
            if t:
                t["_id"] = str(t["_id"])
                tickets.append(t)
        except Exception:
            pass

    inc = _serialize(inc)
    inc["tickets"] = tickets
    return inc


@router.put("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    try:
        oid = ObjectId(incident_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    now = int(datetime.now().timestamp() * 1000)
    result = await db.master_incidents.update_one(
        {"_id": oid},
        {"$set": {"status": "resolved", "updated_at": now}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Master incident resolved"}


@router.get("/kb/articles")
async def list_kb_articles(
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    articles = []
    async for a in db.kb_articles.find().sort("created_at", -1).limit(50):
        a["_id"] = str(a["_id"])
        articles.append(a)
    return articles


@router.get("/kb/articles/{article_id}")
async def get_kb_article(
    article_id: str,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    try:
        article = await db.kb_articles.find_one({"_id": ObjectId(article_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article["_id"] = str(article["_id"])
    return article


@router.post("/kb/articles/generate")
async def generate_kb_article(
    body: dict,
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    ticket_id = body.get("ticket_id")
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticket_id required")
    try:
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    from main import _model_loader, _kb
    from services.kb_service import KBService
    svc = KBService(_model_loader, _kb)
    article = await svc.generate_from_ticket(ticket, db)
    if not article:
        raise HTTPException(
            status_code=422,
            detail="Ticket has no resolution steps to generate KB article from",
        )
    article["_id"] = str(article["_id"])
    return article


@router.post("/kb/articles/{article_id}/feedback")
async def kb_article_feedback(
    article_id: str,
    body: dict,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    rating = body.get("rating")
    if rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="rating must be 'positive' or 'negative'")
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    inc_field = "positive_feedback" if rating == "positive" else "negative_feedback"
    now = int(datetime.now().timestamp() * 1000)
    await db.kb_articles.update_one(
        {"_id": oid},
        {"$inc": {inc_field: 1}, "$set": {"updated_at": now}},
    )

    article = await db.kb_articles.find_one({"_id": oid})
    if article:
        pos   = article.get("positive_feedback", 0)
        neg   = article.get("negative_feedback", 0)
        total = pos + neg
        score = round((pos / total) * 100) if total > 0 else None
        await db.kb_articles.update_one({"_id": oid}, {"$set": {"effectiveness_score": score}})

    return {"message": "Feedback recorded"}
