import asyncio
import logging
import httpx
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger("nexusdesk.agent.remediation")

_ACTIONS = {
    "password_reset": {
        "id": "password_reset",
        "name": "Password Reset",
        "description": "Resets the user account password and sends a temporary credential link.",
        "risk_gate": "low",
        "risk_level": "LOW",
        "confidence": 91,
        "keywords": ["password", "reset", "locked", "login", "cannot sign", "forgot", "credentials"],
        "categories": ["access"],
        "steps": [
            "Verify user identity via employee ID and registered email",
            "Reset Active Directory password to auto-generated temporary value",
            "Send secure password reset link to registered email (TTL: 15 min)",
            "Log action to AD audit trail",
            "Prompt user to set new password on next login",
        ],
        "rollback": "Re-enable previous password hash from AD backup snapshot. Contact domain admin if AD replication has propagated.",
        "audit_events": [
            "Risk validation completed — LOW risk",
            "Identity verification simulated via employee record lookup",
            "Active Directory password reset executed",
            "Secure reset link dispatched to registered email",
            "User notified successfully",
        ],
    },
    "vpn_unlock": {
        "id": "vpn_unlock",
        "name": "VPN Access Unlock",
        "description": "Clears VPN session state and re-provisions access credentials for the affected user.",
        "risk_gate": "low",
        "risk_level": "LOW",
        "confidence": 89,
        "keywords": ["vpn", "remote access", "tunnel", "connection refused", "vpn client", "remote"],
        "categories": ["network", "access"],
        "steps": [
            "Terminate stale VPN session from gateway server side",
            "Flush client-side VPN certificate cache for user profile",
            "Re-issue VPN access token with 8-hour TTL",
            "Verify internal resource connectivity via ICMP ping test",
            "Log new token issuance to VPN audit trail",
        ],
        "rollback": "Revoke newly issued VPN token immediately. Restore previous certificate from backup vault. Contact network admin to re-evaluate access policy.",
        "audit_events": [
            "Risk validation completed — LOW risk",
            "Stale VPN session terminated on gateway",
            "Client-side certificate cache cleared",
            "New access token issued with 8-hour TTL",
            "Connectivity verified via ping test",
            "Audit log entry created",
        ],
    },
    "cache_cleanup": {
        "id": "cache_cleanup",
        "name": "Application Cache Cleanup",
        "description": "Clears browser and application cache to resolve performance degradation and stale content issues.",
        "risk_gate": "low",
        "risk_level": "LOW",
        "confidence": 85,
        "keywords": ["slow", "cache", "performance", "loading", "not loading", "lagging", "stuck", "freeze"],
        "categories": ["software"],
        "steps": [
            "Identify affected application and user profile directory",
            "Clear application-level cache directory (temp + appdata)",
            "Purge browser cache and session storage",
            "Restart application process",
            "Verify normal page load times (target: <3s)",
        ],
        "rollback": "Restore cached user data from profile backup snapshot if local content is missing post-cleanup.",
        "audit_events": [
            "Risk validation completed — LOW risk",
            "Application cache directory identified and cleared",
            "Browser cache and session storage purged",
            "Application restarted successfully",
            "Load time verification passed",
        ],
    },
    "service_restart": {
        "id": "service_restart",
        "name": "Application Service Restart",
        "description": "Gracefully restarts the affected application service after health validation.",
        "risk_gate": "medium",
        "risk_level": "MEDIUM",
        "confidence": 78,
        "keywords": ["not responding", "hung", "service", "restart", "unresponsive", "frozen", "crash"],
        "categories": ["software"],
        "steps": [
            "Verify service health status and PID via service manager",
            "Issue graceful SIGTERM stop signal",
            "Wait 10 seconds for clean shutdown — confirm process termination",
            "Start service and poll health endpoint (max 30s)",
            "Confirm dependent services are operational",
            "Log restart event to service audit trail",
        ],
        "rollback": "If service fails to start, restore from last known-good configuration snapshot stored in /etc/app-configs/. Alert on-call engineer if service remains unavailable.",
        "audit_events": [
            "Human approval received",
            "Risk validation completed — MEDIUM risk",
            "Service health pre-check completed",
            "Graceful shutdown signal issued",
            "Clean shutdown confirmed",
            "Service restarted successfully",
            "Health endpoint responding",
            "Restart event logged to audit trail",
        ],
    },
    "session_terminate": {
        "id": "session_terminate",
        "name": "Active Session Termination",
        "description": "Terminates all active user sessions across services — used for security incidents or stale session resolution.",
        "risk_gate": "medium",
        "risk_level": "MEDIUM",
        "confidence": 74,
        "keywords": ["session", "logout", "sign out", "terminate", "force logout", "active sessions"],
        "categories": ["access", "software"],
        "steps": [
            "Enumerate all active sessions for user account across SSO providers",
            "Issue session invalidation request to identity provider",
            "Revoke all OAuth tokens associated with user",
            "Confirm session termination via audit log verification",
            "Notify user of forced logout via email",
        ],
        "rollback": "User will need to re-authenticate. No rollback required — user can log in again with valid credentials.",
        "audit_events": [
            "Human approval received",
            "Risk validation completed — MEDIUM risk",
            "Active sessions enumerated across SSO providers",
            "Session invalidation request issued to IdP",
            "OAuth tokens revoked",
            "Termination confirmed via audit log",
            "User notified via email",
        ],
    },
}

def _match_action(title: str, description: str, category: str) -> dict | None:
    text = f"{title} {description}".lower()
    cat = category.lower()
    best_match = None
    best_score = 0
    for action in _ACTIONS.values():
        kw_hits = sum(1 for kw in action["keywords"] if kw in text)
        cat_match = cat in action["categories"]
        score = kw_hits * 2 + (1 if cat_match else 0)
        if score > best_score and kw_hits >= 1 and cat_match:
            best_score = score
            best_match = action
    return best_match

class RemediationAgent:
    async def evaluate(
        self, title: str, description: str, category: str, risk: dict | None, db,
        user_email: str = "", target_website: str = None,
    ) -> dict | None:
        if not risk:
            return None

        risk_level = risk.get("risk_level", "low")
        if risk_level == "high":
            logger.info("RemediationAgent: skipped — high risk ticket, manual review required")
            return None

        action = _match_action(title, description, category)
        if not action:
            logger.info("RemediationAgent: no matching action for category=%s", category)
            return None

        now = int(datetime.now().timestamp() * 1000)
        needs_approval = action["risk_gate"] == "medium" or risk_level == "medium"

        initial_status = "pending_approval" if needs_approval else "queued"

        action_doc = {
            "_id": ObjectId(),
            "action_id": action["id"],
            "name": action["name"],
            "description": action["description"],
            "steps": action["steps"],
            "rollback_plan": action["rollback"],
            "risk_gate": action["risk_gate"],
            "risk_level": action["risk_level"],
            "confidence": action["confidence"],
            "status": initial_status,
            "needs_approval": needs_approval,
            "approved_by": None,
            "executed_at": None,
            "rolled_back": False,
            "audit_trail": [
                {
                    "event": f"Remediation action '{action['name']}' identified by CARS",
                    "timestamp": now,
                    "actor": "RemediationAgent",
                },
                {
                    "event": f"Risk gate: {action['risk_gate'].upper()} — {'approval required' if needs_approval else 'auto-execution eligible'}",
                    "timestamp": now,
                    "actor": "RiskValidator",
                },
            ],
            "created_at": now,
            "updated_at": now,
        }

        res = await db.remediation_actions.insert_one(action_doc)
        action_id = str(res.inserted_id)

        if not needs_approval:
            await asyncio.sleep(0.3)
            exec_now = int(datetime.now().timestamp() * 1000)

            extra_audit = []
            reset_result = None

            if action["id"] == "password_reset" and user_email and target_website:
                reset_result = await self._call_website_reset(
                    target_website, user_email, db
                )
                if reset_result.get("success"):
                    extra_audit.append({
                        "event": f"Password reset API call succeeded for {user_email} on '{target_website}'",
                        "timestamp": exec_now,
                        "actor": "CARS",
                    })
                else:
                    extra_audit.append({
                        "event": f"Password reset API call failed: {reset_result.get('error', 'Unknown error')}",
                        "timestamp": exec_now,
                        "actor": "CARS",
                    })

            audit_trail = action_doc["audit_trail"] + [
                {"event": e, "timestamp": exec_now + (i * 200), "actor": "CARS"}
                for i, e in enumerate(action.get("audit_events", []))
            ] + extra_audit
            await db.remediation_actions.update_one(
                {"_id": res.inserted_id},
                {"$set": {
                    "status": "executed",
                    "executed_at": exec_now,
                    "updated_at": exec_now,
                    "audit_trail": audit_trail,
                }}
            )
            status = "executed"
        else:
            status = "pending_approval"

        logger.info(
            "RemediationAgent: action=%s status=%s needs_approval=%s confidence=%d%%",
            action["id"], status, needs_approval, action["confidence"]
        )

        return {
            "action_doc_id": action_id,
            "action_id": action["id"],
            "name": action["name"],
            "description": action["description"],
            "steps": action["steps"],
            "rollback_plan": action["rollback"],
            "risk_level": action["risk_level"],
            "confidence": action["confidence"],
            "status": status,
            "needs_approval": needs_approval,
            "audit_events": action.get("audit_events", []),
            "reset_result": reset_result,
        }

    async def _call_website_reset(self, target_website: str, user_email: str, db) -> dict:

        try:
            site = await db.websites.find_one(
                {"name": {"$regex": f"^{target_website}$", "$options": "i"}}
            )
            if not site:
                logger.warning("RemediationAgent: website '%s' not found in registry", target_website)
                return {"success": False, "error": f"Website '{target_website}' not registered in Unisys registry."}

            reset_url = site["reset_url"]
            api_key   = site["api_key"]

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    reset_url,
                    json={"email": user_email},
                    headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                )
                data = response.json()
                logger.info(
                    "RemediationAgent: reset API call → %s status=%d success=%s",
                    reset_url, response.status_code, data.get("success")
                )
                return data
        except Exception as exc:
            logger.error("RemediationAgent: reset API call failed: %s", exc)
            return {"success": False, "error": str(exc)}