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
from knowledge_base.kb_loader import KnowledgeBaseLoader
from models.model_loader import ModelLoader
from routers import tickets, auth, logs

_analyzer: TicketAnalyzerAgent | None = None
_resolver: ResolutionAgent | None = None
_risk_agent: RiskAgent | None = None
_escalation_agent: EscalationAgent | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _analyzer, _resolver, _risk_agent, _escalation_agent

    print("[NexusDesk] Loading AI models...")
    loader = ModelLoader()
    kb = KnowledgeBaseLoader(loader)

    _analyzer = TicketAnalyzerAgent(loader)
    _resolver = ResolutionAgent(loader, kb)
    _risk_agent = RiskAgent()
    _escalation_agent = EscalationAgent()

    print("[NexusDesk] Pre-warming BART classifier...")
    _ = loader.classifier
    print("[NexusDesk] All agents ready. API is live.")
    yield
    print("[NexusDesk] Shutting down.")

app = FastAPI(
    title="NexusDesk AI Engine",
    description="Agentic AI backend for enterprise IT support automation.",
    version="1.0.0",
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
    print(f"[ERROR] {request.method} {request.url.path} -> {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
    )

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

app.include_router(tickets.router)
app.include_router(auth.router)
app.include_router(logs.router)

@app.get("/health", tags=["System"])
async def health():
    return {"status": "online", "engine": "NexusDesk AI v1.0"}

@app.post("/analyze", tags=["Agents"])
async def analyze(req: AnalyzeRequest):
    try:
        return await _analyzer.run(req.title or "", req.description)
    except Exception as exc:
        print(f"[/analyze ERROR] {exc}")
        raise

@app.post("/assess-risk", tags=["Agents"])
async def assess_risk(req: RiskRequest):
    try:
        risk = _risk_agent.run(req.title, req.description, req.category, req.priority)
        return _escalation_agent.apply(risk)
    except Exception as exc:
        print(f"[/assess-risk ERROR] {exc}")
        raise

@app.post("/resolve", tags=["Agents"])
async def resolve(req: ResolveRequest):
    try:
        return await _resolver.run(
            req.title,
            req.description,
            req.analysis,
            req.riskAssessment,
        )
    except Exception as exc:
        print(f"[/resolve ERROR] {exc}")
        raise
