from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional, Any

from database import get_db
from auth_deps import require_admin

router = APIRouter(prefix="/copilot", tags=["Copilot"])

class CopilotRequest(BaseModel):
    ticket_id:   str
    title:       str
    description: str
    analysis:    Optional[Any] = None
    risk:        Optional[Any] = None

    @field_validator("title")
    @classmethod
    def cap_title(cls, v: str) -> str:
        return v[:500]

    @field_validator("description")
    @classmethod
    def cap_description(cls, v: str) -> str:
        return v[:4000]

@router.post("/suggest")
async def get_suggestions(
    req: CopilotRequest,
    _user=Depends(require_admin),
):
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