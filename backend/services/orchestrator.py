import asyncio
import logging
from datetime import datetime

from agents.ticket_analyzer import TicketAnalyzerAgent
from agents.risk_agent import RiskAgent
from agents.escalation_agent import EscalationAgent
from agents.resolution_agent import ResolutionAgent
from agents.dedup_agent import DedupAgent
from agents.explain_agent import ExplainAgent
from agents.remediation_agent import RemediationAgent
from services.event_bus import bus

logger = logging.getLogger("nexusdesk.orchestrator")

MAX_RETRIES = 2
SLA_MINUTES_BY_PRIORITY = {"critical": 15, "high": 30, "medium": 120, "low": 480}


def _eta_minutes(priority: str) -> int:
    return SLA_MINUTES_BY_PRIORITY.get(priority, 60)


class AgentOrchestrator:
    def __init__(self, analyzer, risk_agent, escalation_agent, resolver, kb, model_loader):
        self.analyzer = analyzer
        self.risk_agent = risk_agent
        self.escalation_agent = escalation_agent
        self.resolver = resolver
        self.kb = kb
        self.dedup = DedupAgent(model_loader, kb)
        self.explain = ExplainAgent()
        self.remediation = RemediationAgent()

    async def run_pipeline(self, ticket_id, title: str, description: str, db):
        from bson import ObjectId
        tid_str = str(ticket_id)
        loop = asyncio.get_running_loop()

        logger.info("Pipeline START ticket=%s title='%s'", tid_str, title)

        async def _log(agent: str, action: str, details: str):
            await db.admin_logs.insert_one({
                "action": action,
                "agent": agent,
                "ticket_id": tid_str,
                "details": details,
                "timestamp": int(datetime.now().timestamp() * 1000),
            })

        async def _update(fields: dict, history_msg: str, new_status: str):
            now = int(datetime.now().timestamp() * 1000)
            fields["updatedAt"] = now
            await db.tickets.update_one(
                {"_id": ticket_id},
                {
                    "$set": fields,
                    "$push": {"history": {"timestamp": now, "status": new_status, "message": history_msg}},
                },
            )

        async def _mark_failed(step: str, reason: str):
            msg = f"[PIPELINE FAILED] Step '{step}' failed. Reason: {reason[:200]}"
            logger.error("Pipeline FAILED step=%s: %s", step, reason)
            await _log("Pipeline", "pipeline_failed", msg)
            await _update(
                {
                    "status": "failed",
                    "employee_response": (
                        "We encountered an issue processing your request automatically. "
                        "Our IT team has been notified and will review your ticket manually."
                    ),
                    "admin_response": f"PIPELINE FAILURE at step: {step}. {reason}",
                },
                msg, "failed",
            )

        async def _with_retry(step_name: str, coro_factory):
            last_exc = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    return await coro_factory()
                except Exception as exc:
                    last_exc = exc
                    wait = attempt * 2
                    logger.warning(
                        "Step %s attempt %d/%d failed: %s. Retry in %ds",
                        step_name, attempt, MAX_RETRIES, exc, wait
                    )
                    await _log(step_name, f"step_retry_{attempt}", f"Attempt {attempt} failed: {str(exc)[:200]}")
                    await asyncio.sleep(wait)
            raise last_exc

        await _update({"status": "in_progress"}, "Agentic orchestration workflow started.", "in_progress")

        # ── Step 1: Deduplication ──────────────────────────────────
        dedup_result = await self.dedup.check(title, description, db, exclude_id=ticket_id)

        if dedup_result.get("is_duplicate"):
            await self._handle_duplicate(
                ticket_id, tid_str, title, description,
                dedup_result, db, _log, _update, loop
            )
            return

        # ── Step 2: Ticket Analysis ────────────────────────────────
        analysis = None
        if self.analyzer:
            try:
                analysis = await _with_retry("TicketAnalyzer", lambda: self.analyzer.run(title, description))
                await db.tickets.update_one(
                    {"_id": ticket_id},
                    {"$set": {
                        "priority": analysis.get("suggestedPriority", "medium"),
                        "category": analysis.get("suggestedCategory", "other"),
                        "analysis": analysis,
                    }},
                )
                await _log("TicketAnalyzer", "analysis_complete",
                    f"Category: {analysis.get('suggestedCategory')} | "
                    f"Priority: {analysis.get('suggestedPriority')} | "
                    f"Confidence: {round(analysis.get('confidenceScore', 0) * 100)}%")
            except Exception as exc:
                await _mark_failed("TicketAnalyzer", str(exc))
                return

        # ── Step 3: Risk Assessment ────────────────────────────────
        risk = None
        if self.risk_agent:
            try:
                _priority = (analysis or {}).get("suggestedPriority", "medium")
                _category = (analysis or {}).get("suggestedCategory", "other")
                risk = await _with_retry("RiskAgent", lambda: loop.run_in_executor(
                    None, self.risk_agent.run, title, description, _category, _priority
                ))
                await _log("RiskAgent", "risk_assessed",
                    f"Risk: {risk.get('risk_level','?').upper()} | "
                    f"Score: {round(risk.get('riskScore', 0) * 100)}% | "
                    f"Security: {risk.get('securityRisk', False)} | "
                    f"Confidence: {risk.get('confidence_score', '?')}%")
            except Exception as exc:
                await _mark_failed("RiskAgent", str(exc))
                return

        # ── Step 4: Escalation ─────────────────────────────────────
        if self.escalation_agent and risk:
            try:
                risk = await _with_retry("EscalationAgent", lambda: loop.run_in_executor(
                    None, self.escalation_agent.apply, risk, False
                ))
                await _log("EscalationAgent", "escalation_decision",
                    f"Escalate: {risk.get('escalate')} | "
                    f"LowConf: {risk.get('low_confidence')} | "
                    f"Status: {risk.get('final_status', '?')}")
            except Exception as exc:
                await _mark_failed("EscalationAgent", str(exc))
                return

        # ── Step 5: Controlled Automated Remediation ───────────────
        _category = (analysis or {}).get("suggestedCategory", "other")
        remediation_result = await self.remediation.evaluate(title, description, _category, risk, db)
        if remediation_result:
            await db.tickets.update_one(
                {"_id": ticket_id},
                {"$set": {"remediation_action": remediation_result}}
            )
            await _log("RemediationAgent", "remediation_evaluated",
                f"Action: {remediation_result['name']} | "
                f"Status: {remediation_result['status']} | "
                f"NeedsApproval: {remediation_result['needs_approval']}")

        # ── Step 6: Resolution via RAG ─────────────────────────────
        resolution = None
        final_status = "in_progress"
        if self.resolver:
            try:
                resolution = await _with_retry("ResolutionAgent", lambda: self.resolver.run(
                    title, description, analysis, risk
                ))
                automated = resolution.get("automated", False)
                if self.escalation_agent and risk:
                    risk = self.escalation_agent.apply(risk, automated=automated)
                final_status = risk.get("final_status", "in_progress") if risk else "in_progress"
                risk_level = (risk or {}).get("risk_level", "low")
                confidence_score = (risk or {}).get("confidence_score")
                low_confidence = (risk or {}).get("low_confidence", False)

                await _log("ResolutionAgent", "resolution_generated",
                    f"KB: {resolution.get('kbTitle', 'N/A')} | "
                    f"Automated: {automated} | Status: {final_status}")
            except Exception as exc:
                await _mark_failed("ResolutionAgent", str(exc))
                return

        # ── Step 7: Explainability ─────────────────────────────────
        explanation = self.explain.build(
            title, description, analysis, risk,
            dedup_result=None,
            resolution=resolution,
            remediation=remediation_result,
        )
        confidence_map = explanation.get("confidence_map", {})
        await db.tickets.update_one(
            {"_id": ticket_id},
            {"$set": {"ai_explanation": explanation, "confidence_map": confidence_map}}
        )
        await _log("ExplainAgent", "explanation_generated",
            f"Overall AI confidence: {explanation.get('overall_ai_confidence')}% | "
            f"Sentiment: {explanation.get('sentiment')}")

        # ── Step 8: Final Update ───────────────────────────────────
        if resolution:
            employee_response = resolution.get("employee_response") or "Your request is under review by our IT team."
            admin_response = resolution.get("admin_response") or ""
            await _update(
                {
                    "status": final_status,
                    "riskAssessment": risk,
                    "resolution": resolution,
                    "employee_response": employee_response,
                    "admin_response": admin_response,
                    "risk_level": risk_level,
                    "confidence_score": confidence_score,
                    "low_confidence": low_confidence,
                },
                f"Agentic workflow complete. Status: {final_status.upper()}. "
                f"Risk: {(risk or {}).get('risk_level', 'low').upper()}. "
                f"{'Controlled remediation applied.' if (resolution or {}).get('automated') else 'Awaiting IT agent.'}",
                final_status,
            )

        # ── Step 9: Learning Loop ──────────────────────────────────
        try:
            if (self.kb and risk and resolution and
                    final_status == "resolved" and
                    risk.get("risk_level") == "low" and
                    resolution.get("steps")):
                self.kb.add_resolved_ticket(
                    ticket_id=tid_str,
                    title=title,
                    description=description,
                    steps=resolution["steps"],
                    result=resolution.get("result", "Resolved via agentic workflow."),
                    category=(analysis or {}).get("suggestedCategory", "other"),
                )
                await _log("LearningLoop", "kb_entry_added", f"Ticket '{title}' added to knowledge base.")

                full_ticket = await db.tickets.find_one({"_id": ticket_id})
                if full_ticket:
                    from services.kb_service import KBService
                    from main import _model_loader, _kb
                    kb_svc = KBService(_model_loader, _kb)
                    await kb_svc.generate_from_ticket(full_ticket, db)
        except Exception as exc:
            logger.warning("LearningLoop non-critical error: %s", exc)

        await bus.emit("ticket.resolved" if final_status == "resolved" else "pipeline.complete", {
            "ticket_id": tid_str, "status": final_status
        })
        logger.info("Pipeline COMPLETE ticket=%s status=%s", tid_str, final_status)

    async def _handle_duplicate(
        self, ticket_id, tid_str, title, description,
        dedup_result, db, _log, _update, loop
    ):
        from bson import ObjectId as OID

        canonical_id = dedup_result["duplicate_of"]
        sim = dedup_result.get("similarity_score", 0)
        conf = dedup_result.get("confidence", 0)

        logger.info("Pipeline DEDUP: ticket=%s linked_to=%s sim=%.2f", tid_str, canonical_id, sim)

        # Fetch canonical ticket for context
        canonical = None
        try:
            canonical = await db.tickets.find_one(
                {"_id": OID(canonical_id)},
                {"title": 1, "status": 1, "priority": 1, "resolution": 1,
                 "category": 1, "analysis": 1, "employee_response": 1}
            )
        except Exception:
            pass

        # Retrieve workaround from the canonical ticket's resolution or KB
        workaround_steps = []
        workaround_source = None
        canonical_employee_response = (canonical or {}).get("employee_response", "")

        if canonical and canonical.get("resolution", {}).get("steps"):
            workaround_steps = canonical["resolution"]["steps"]
            workaround_source = canonical["resolution"].get("kbTitle", "Canonical Incident")
        elif self.resolver:
            try:
                analysis_hint = (canonical or {}).get("analysis")
                resolution = await self.resolver.run(title, description, analysis_hint, None)
                workaround_steps = resolution.get("steps", [])
                workaround_source = resolution.get("kbTitle", "Knowledge Base")
                # Filter out generic "no match" steps
                workaround_steps = [
                    s for s in workaround_steps
                    if "no matching resolution" not in s.lower()
                    and "escalate to level" not in s.lower()
                    and "attach system logs" not in s.lower()
                ]
            except Exception as exc:
                logger.warning("Dedup workaround retrieval failed: %s", exc)

        # Determine canonical status and ETA
        canonical_status = (canonical or {}).get("status", "in_progress")
        canonical_priority = (canonical or {}).get("priority", "medium")
        eta_minutes = _eta_minutes(canonical_priority)

        if canonical_status == "resolved":
            eta_minutes = 0
            eta_label = "Already resolved — applying fix now"
        elif canonical_status == "escalated":
            eta_label = f"Under active investigation — estimated {eta_minutes} min"
        else:
            eta_label = f"Under investigation — estimated {eta_minutes}–{eta_minutes + 10} min"

        # Build structured employee response — always include a solution
        workaround_text = ""
        if workaround_steps:
            steps_list = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(workaround_steps[:6]))
            workaround_text = (
                f"\n\nSuggested Workaround (from {workaround_source or 'KB'}):\n{steps_list}"
            )
        elif canonical_employee_response and canonical_status == "resolved":
            # The canonical ticket was resolved — share its solution directly
            workaround_text = (
                f"\n\nResolution Applied to Original Incident:\n{canonical_employee_response}"
            )
        elif canonical_employee_response:
            # Canonical ticket has an AI response — surface it as context
            workaround_text = (
                f"\n\nAI Response from Original Incident:\n"
                + "\n".join(
                    f"  {line}" for line in canonical_employee_response.splitlines()
                    if line.strip()
                )[:1500]
            )

        employee_response = (
            f"Linked Incident Detected\n"
            f"Your issue has been identified as part of an existing incident that is currently being investigated.\n"
            f"{workaround_text}\n\n"
            f"Incident Status: {canonical_status.replace('_', ' ').title()}\n"
            f"Estimated Resolution: {eta_label}\n"
            f"AI Confidence: {conf}%\n\n"
            f"You will be notified automatically as soon as the incident is resolved."
        )

        # Build explainability for the dedup decision
        explanation = self.explain.build(
            title, description,
            analysis=(canonical or {}).get("analysis"),
            risk=None,
            dedup_result=dedup_result,
            resolution={"steps": workaround_steps, "kbTitle": workaround_source} if workaround_steps else None,
            remediation=None,
        )

        # Update the duplicate ticket with full context
        now = int(datetime.now().timestamp() * 1000)
        await db.tickets.update_one(
            {"_id": ticket_id},
            {"$set": {
                "status": "linked",
                "duplicate_of": canonical_id,
                "dedup_confidence": sim,
                "employee_response": employee_response,
                "admin_response": (
                    f"[DEDUP] Linked to #{canonical_id[:12]} "
                    f"(similarity={round(sim*100)}%, confidence={conf}%). "
                    f"Workaround: {workaround_source or 'None retrieved'}. "
                    f"Canonical status: {canonical_status}."
                ),
                "ai_explanation": explanation,
                "confidence_map": explanation.get("confidence_map", {}),
                "workaround_steps": workaround_steps,
                "canonical_incident_id": canonical_id,
                "canonical_status": canonical_status,
                "eta_label": eta_label,
                "eta_minutes": eta_minutes,
                "updatedAt": now,
            }}
        )

        # Update canonical ticket — add this user as affected
        try:
            await db.tickets.update_one(
                {"_id": OID(canonical_id)},
                {
                    "$addToSet": {"affected_users": tid_str},
                    "$inc": {"linked_count": 1},
                }
            )
        except Exception:
            pass

        await _log(
            "DedupAgent", "duplicate_detected",
            f"Linked to {canonical_id} (sim={round(sim*100)}%, conf={conf}%). "
            f"Workaround retrieved: {bool(workaround_steps)}. "
            f"Canonical status: {canonical_status}. ETA: {eta_label}"
        )

        await bus.emit("ticket.linked", {
            "ticket_id": tid_str,
            "canonical_id": canonical_id,
            "similarity": sim,
        })
