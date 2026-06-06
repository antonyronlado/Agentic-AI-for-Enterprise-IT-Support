import asyncio
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger("nexusdesk.agent.rca")

try:
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available — RCA clustering disabled")

def _derive_root_cause(tickets: list[dict]) -> tuple[str, str]:
    categories = [t.get("category", "other") for t in tickets]
    majority_cat = max(set(categories), key=categories.count)

    all_text = " ".join(
        f"{t.get('title', '')} {t.get('description', '')}" for t in tickets
    ).lower()

    infra_patterns = {
        "network": ["network", "vpn", "connectivity", "dns", "firewall", "latency"],
        "access": ["password", "login", "authentication", "locked", "credentials"],
        "software": ["crash", "error", "application", "update", "install"],
        "hardware": ["device", "printer", "monitor", "keyboard", "hardware"],
    }

    pattern_hits = {k: sum(1 for w in v if w in all_text) for k, v in infra_patterns.items()}
    top_pattern = max(pattern_hits, key=pattern_hits.get) if any(pattern_hits.values()) else majority_cat

    cause_map = {
        "network": "Possible infrastructure-level network degradation affecting multiple users",
        "access": "Possible Active Directory / identity provider issue causing access failures",
        "software": "Possible application-level failure or failed deployment affecting user sessions",
        "hardware": "Possible hardware provisioning or driver rollout issue across endpoints",
        "other": "Multiple users reporting similar issues — possible shared service disruption",
    }
    return cause_map.get(top_pattern, cause_map["other"]), majority_cat

class RCAAgent:
    def __init__(self, model_loader):
        self.model_loader = model_loader

    async def cluster_tickets(self, db) -> list[dict]:
        if not SKLEARN_AVAILABLE:
            return []

        tickets = []
        cursor = db.tickets.find(
            {"status": {"$in": ["open", "in_progress", "escalated"]}, "duplicate_of": None},
            {"_id": 1, "title": 1, "description": 1, "category": 1, "userId": 1}
        )
        async for t in cursor:
            tickets.append(t)

        if len(tickets) < 2:
            return []

        loop = asyncio.get_running_loop()
        clusters = await loop.run_in_executor(None, self._run_clustering, tickets)

        now = int(datetime.now().timestamp() * 1000)
        master_incidents = []

        for cluster_tickets in clusters:
            if len(cluster_tickets) < 2:
                continue

            root_cause, category = _derive_root_cause(cluster_tickets)
            ticket_ids = [str(t["_id"]) for t in cluster_tickets]
            user_ids = list({t.get("userId", "") for t in cluster_tickets if t.get("userId")})

            texts = [
                f"{t.get('title', '')}. {t.get('description', '')}"
                for t in cluster_tickets
            ]
            embs = self.model_loader.embedder.encode(texts, normalize_embeddings=True)
            embs = np.array(embs, dtype=np.float32)
            coherence = float(np.mean(embs @ embs.T))
            cluster_confidence = round(min(coherence * 100, 99))

            severity = "high" if len(cluster_tickets) >= 5 else "medium" if len(cluster_tickets) >= 3 else "low"

            existing = await db.master_incidents.find_one({"affected_ticket_ids": {"$in": ticket_ids}})

            if existing:
                await db.master_incidents.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "affected_ticket_ids": ticket_ids,
                        "affected_user_count": len(user_ids),
                        "cluster_confidence": cluster_confidence,
                        "severity": severity,
                        "updated_at": now,
                    }}
                )
                inc_id = str(existing["_id"])
            else:
                from bson import ObjectId
                inc_doc = {
                    "_id": ObjectId(),
                    "title": f"Cluster: {root_cause[:60]}",
                    "probable_root_cause": root_cause,
                    "affected_ticket_ids": ticket_ids,
                    "affected_user_count": len(user_ids),
                    "category": category,
                    "severity": severity,
                    "cluster_confidence": cluster_confidence,
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                }
                res = await db.master_incidents.insert_one(inc_doc)
                inc_id = str(res.inserted_id)

            for tid in ticket_ids:
                from bson import ObjectId as OID
                await db.tickets.update_one(
                    {"_id": OID(tid)},
                    {"$set": {"master_incident_id": inc_id}}
                )

            master_incidents.append({
                "id": inc_id,
                "title": f"Cluster: {root_cause[:60]}",
                "probable_root_cause": root_cause,
                "affected_ticket_ids": ticket_ids,
                "affected_user_count": len(user_ids),
                "category": category,
                "severity": severity,
                "cluster_confidence": cluster_confidence,
            })

        logger.info("RCAAgent: produced %d incident clusters", len(master_incidents))
        return master_incidents

    def _run_clustering(self, tickets: list[dict]) -> list[list[dict]]:
        texts = [
            f"{t.get('title', '')}. {t.get('description', '')}"
            for t in tickets
        ]
        embeddings = self.model_loader.embedder.encode(texts, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)

        distance_matrix = 1.0 - (embeddings @ embeddings.T)
        distance_matrix = np.clip(distance_matrix, 0, 2)

        db = DBSCAN(eps=0.25, min_samples=2, metric="precomputed")
        labels = db.fit_predict(distance_matrix)

        cluster_map: dict[int, list] = {}
        for idx, label in enumerate(labels):
            if label == -1:
                continue
            cluster_map.setdefault(label, []).append(tickets[idx])

        return list(cluster_map.values())