from fastapi import APIRouter, Depends

from database import get_db
from auth_deps import require_admin

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
async def overview(
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    from main import _trend_agent
    if not _trend_agent:
        return {}
    return await _trend_agent.get_overview(db)

@router.get("/trends")
async def trends(
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    from main import _trend_agent
    if not _trend_agent:
        return {}
    return await _trend_agent.get_trends(db)

@router.get("/trend-intelligence")
async def trend_intelligence(
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    from main import _trend_agent
    if not _trend_agent:
        return {}
    return await _trend_agent.get_trend_intelligence(db)

@router.get("/resolution-perf")
async def resolution_perf(
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    from main import _trend_agent
    if not _trend_agent:
        return {}
    data = await _trend_agent.get_overview(db)
    return {
        "ai_resolution_pct":      data.get("ai_resolution_pct", 0),
        "sla_compliance":         data.get("sla_compliance", 0),
        "escalation_rate":        data.get("escalation_rate", 0),
        "avg_resolution_minutes": data.get("avg_resolution_minutes", 0),
    }