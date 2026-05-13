from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from database import get_db

router = APIRouter(prefix="/copilot", tags=["Copilot"])


class CopilotRequest(BaseModel):
    ticket_id: str
    title: str
    description: str
    analysis: Optional[Any] = None
    risk: Optional[Any] = None


@router.post("/suggest")
async def get_suggestions(req: CopilotRequest):
    from main import _copilot_agent
    if not _copilot_agent:
        raise HTTPException(status_code=503, detail="Copilot agent not initialized")

    result = await _copilot_agent.suggest(
        title=req.title,
        description=req.description,
        analysis=req.analysis,
        risk=req.risk,
    )
    return result
