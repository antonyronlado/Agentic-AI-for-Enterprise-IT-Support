import asyncio
import logging
import os
import config

from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from agents.escalation_agent import EscalationAgent
from agents.resolution_agent import ResolutionAgent
from agents.risk_agent import RiskAgent
from agents.ticket_analyzer import TicketAnalyzerAgent
from agents.rca_agent import RCAAgent
from agents.copilot_agent import CopilotAgent
from agents.trend_agent import TrendAgent
from knowledge_base.kb_loader import KnowledgeBaseLoader
from models.model_loader import ModelLoader
from routers import tickets, auth, logs
from routers import incidents, copilot, analytics, automation, multimodal
from routers import websites
from sla_monitor import run_sla_monitor
from auth_deps import require_auth

logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s][%(levelname)s] %(message)s",
)
logger = logging.getLogger("nexusdesk.main")

_analyzer:         TicketAnalyzerAgent | None = None
_resolver:         ResolutionAgent     | None = None
_risk_agent:       RiskAgent           | None = None
_escalation_agent: EscalationAgent     | None = None
_kb:               KnowledgeBaseLoader | None = None
_rca_agent:        RCAAgent            | None = None
_copilot_agent:    CopilotAgent        | None = None
_trend_agent:      TrendAgent          | None = None
_model_loader:     ModelLoader         | None = None
_sla_task:         asyncio.Task        | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _analyzer, _resolver, _risk_agent, _escalation_agent, _kb
    global _rca_agent, _copilot_agent, _trend_agent, _model_loader, _sla_task

    logger.info("Loading AI models...")
    loader = ModelLoader()
    _model_loader = loader

    logger.info("Building knowledge base index...")
    _kb = await asyncio.to_thread(KnowledgeBaseLoader, loader)

    _analyzer         = TicketAnalyzerAgent(loader)
    _resolver         = ResolutionAgent(loader, _kb)
    _risk_agent       = RiskAgent()
    _escalation_agent = EscalationAgent()
    _rca_agent        = RCAAgent(loader)
    _copilot_agent    = CopilotAgent(loader, _kb)
    _trend_agent      = TrendAgent()

    async def _prewarm_classifier():
        try:
            logger.info("Pre-warming BART classifier in background...")
            await asyncio.to_thread(lambda: loader.classifier)
            logger.info("BART classifier ready.")
        except Exception:
            logger.exception("BART pre-warm failed; will retry on first request.")

    asyncio.create_task(_prewarm_classifier())

    from database import get_db
    _sla_task = asyncio.create_task(run_sla_monitor(get_db))
    logger.info("SLA Monitor started.")
    logger.info("NexusDesk is live. AI classifier may still be loading in the background.")
    yield

    if _sla_task:
        _sla_task.cancel()
        try:
            await _sla_task
        except asyncio.CancelledError:
            pass
    logger.info("NexusDesk shutting down.")

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app = FastAPI(
    title="NexusDesk AI Engine",
    description="Agentic AI Workflow Platform for Enterprise IT Operations.",
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception: %s %s -> %s: %s",
        request.method, request.url.path, type(exc).__name__, exc,
        exc_info=True,
    )
    origin      = request.headers.get("origin", "")
    allow_origin = origin if origin in ALLOWED_ORIGINS else (ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later."},
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )

app.include_router(tickets.router)
app.include_router(auth.router)
app.include_router(logs.router)
app.include_router(incidents.router)
app.include_router(copilot.router)
app.include_router(analytics.router)
app.include_router(automation.router)
app.include_router(multimodal.router)
app.include_router(websites.router)

@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "online",
        "engine": "NexusDesk AI v3.1",
        "platform": "Enterprise AI-Native IT Operations Platform",
        "features": [
            "agentic-orchestration",
            "ticket-deduplication",
            "rca-clustering",
            "explainable-ai",
            "controlled-automated-remediation",
            "ai-copilot",
            "incident-trend-intelligence",
            "smart-kb-generation",
            "multimodal-analysis",
            "feedback-learning-loop",
        ],
    }

class AnalyzeRequest(BaseModel):
    title: Optional[str] = ""
    description: str

    @field_validator("description")
    @classmethod
    def cap_description(cls, v: str) -> str:
        return v[:4000]

    @field_validator("title")
    @classmethod
    def cap_title(cls, v: str) -> str:
        return (v or "")[:500]

class RiskRequest(BaseModel):
    title: str
    description: str
    category: Optional[str] = "other"
    priority: Optional[str] = "medium"

    @field_validator("title")
    @classmethod
    def cap_title(cls, v: str) -> str:
        return v[:500]

    @field_validator("description")
    @classmethod
    def cap_description(cls, v: str) -> str:
        return v[:4000]

class ResolveRequest(BaseModel):
    title: str
    description: str
    analysis: Optional[Any] = None
    riskAssessment: Optional[Any] = None

    @field_validator("title")
    @classmethod
    def cap_title(cls, v: str) -> str:
        return v[:500]

    @field_validator("description")
    @classmethod
    def cap_description(cls, v: str) -> str:
        return v[:4000]

@app.post("/analyze", tags=["Agents"])
async def analyze(req: AnalyzeRequest, _user=Depends(require_auth)):
    return await _analyzer.run(req.title or "", req.description)

@app.post("/assess-risk", tags=["Agents"])
async def assess_risk(req: RiskRequest, _user=Depends(require_auth)):
    risk = _risk_agent.run(req.title, req.description, req.category, req.priority)
    return _escalation_agent.apply(risk)

@app.post("/resolve", tags=["Agents"])
async def resolve(req: ResolveRequest, _user=Depends(require_auth)):
    return await _resolver.run(req.title, req.description, req.analysis, req.riskAssessment)

class LearnRequest(BaseModel):
    ticket_id:   str
    title:       str
    description: str
    steps:       list[str]
    result:      str
    category:    Optional[str] = "other"

    @field_validator("title")
    @classmethod
    def cap_title(cls, v: str) -> str:
        return v[:500]

    @field_validator("description")
    @classmethod
    def cap_description(cls, v: str) -> str:
        return v[:4000]

    @field_validator("steps")
    @classmethod
    def cap_steps(cls, v: list) -> list:
        return [s[:500] for s in v[:20]]

@app.post("/learn", tags=["Learning"])
async def learn_from_ticket(req: LearnRequest, _user=Depends(require_auth)):
    if not _kb:
        return JSONResponse(status_code=503, content={"error": "KB not initialized"})
    added = _kb.add_resolved_ticket(
        ticket_id=req.ticket_id,
        title=req.title,
        description=req.description,
        steps=req.steps,
        result=req.result,
        category=req.category,
    )
    return {
        "added": added,
        "message": "Entry added to knowledge base." if added else "Duplicate — entry already exists.",
        "total_entries": len(_kb.entries),
    }