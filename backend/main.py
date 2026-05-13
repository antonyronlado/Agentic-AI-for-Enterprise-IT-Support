import asyncio
import logging
import config

from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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
from sla_monitor import run_sla_monitor

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

    logger.info("Pre-warming BART classifier...")
    await asyncio.to_thread(lambda: loader.classifier)

    from database import get_db
    _sla_task = asyncio.create_task(run_sla_monitor(get_db))
    logger.info("SLA Monitor started.")
    logger.info("All agents ready. NexusDesk Enterprise AI-Native IT Operations Platform is live.")
    yield

    if _sla_task:
        _sla_task.cancel()
        try:
            await _sla_task
        except asyncio.CancelledError:
            pass
    logger.info("NexusDesk shutting down.")


app = FastAPI(
    title="NexusDesk AI Engine",
    description="Agentic AI Workflow Platform for Enterprise IT Operations.",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("%s %s -> %s: %s", request.method, request.url.path, type(exc).__name__, exc)
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
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


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "online",
        "engine": "NexusDesk AI v3.0",
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


class RiskRequest(BaseModel):
    title: str
    description: str
    category: Optional[str] = "other"
    priority: Optional[str] = "medium"


class ResolveRequest(BaseModel):
    title: str
    description: str
    analysis: Optional[Any] = None
    riskAssessment: Optional[Any] = None


@app.post("/analyze", tags=["Agents"])
async def analyze(req: AnalyzeRequest):
    return await _analyzer.run(req.title or "", req.description)


@app.post("/assess-risk", tags=["Agents"])
async def assess_risk(req: RiskRequest):
    risk = _risk_agent.run(req.title, req.description, req.category, req.priority)
    return _escalation_agent.apply(risk)


@app.post("/resolve", tags=["Agents"])
async def resolve(req: ResolveRequest):
    return await _resolver.run(req.title, req.description, req.analysis, req.riskAssessment)


class LearnRequest(BaseModel):
    ticket_id:   str
    title:       str
    description: str
    steps:       list[str]
    result:      str
    category:    Optional[str] = "other"


@app.post("/learn", tags=["Learning"])
async def learn_from_ticket(req: LearnRequest):
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
