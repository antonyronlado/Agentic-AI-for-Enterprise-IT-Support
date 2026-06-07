import logging
from datetime import datetime, timedelta

logger = logging.getLogger("nexusdesk.agent.trend")

SPIKE_MULTIPLIER = 2.0
RECURRING_THRESHOLD = 3

class TrendAgent:
    def __init__(self):
        self._cache: dict = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 1800.0

    async def get_overview(self, db) -> dict:
        now = int(datetime.now().timestamp() * 1000)

        total = await db.tickets.count_documents({})
        by_status = {}
        for s in ["open", "in_progress", "escalated", "resolved", "failed", "linked"]:
            by_status[s] = await db.tickets.count_documents({"status": s})

        by_category = {}
        for c in ["software", "hardware", "access", "network", "other"]:
            by_category[c] = await db.tickets.count_documents({"category": c})

        by_priority = {}
        for p in ["critical", "high", "medium", "low"]:
            by_priority[p] = await db.tickets.count_documents({"priority": p})

        sla_window_ms = 4 * 60 * 60 * 1000
        resolved_in_sla = await db.tickets.count_documents({
            "status": "resolved",
            "$expr": {"$lte": [{"$subtract": ["$updatedAt", "$createdAt"]}, sla_window_ms]}
        })
        resolved_total = by_status.get("resolved", 0)
        sla_compliance = round((resolved_in_sla / resolved_total * 100) if resolved_total else 0)

        ai_resolved = await db.tickets.count_documents({
            "status": "resolved",
            "resolution.automated": True
        })
        ai_pct = round((ai_resolved / resolved_total * 100) if resolved_total else 0)

        escalated = by_status.get("escalated", 0)
        esc_rate = round((escalated / total * 100) if total else 0)

        pipeline_result = []
        async for doc in db.tickets.aggregate([
            {"$match": {"status": "resolved"}},
            {"$project": {"duration": {"$subtract": ["$updatedAt", "$createdAt"]}}},
            {"$group": {"_id": None, "avg": {"$avg": "$duration"}}}
        ]):
            pipeline_result.append(doc)

        avg_ms = pipeline_result[0]["avg"] if pipeline_result else 0
        avg_minutes = round(avg_ms / 60000) if avg_ms else 0

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "by_priority": by_priority,
            "sla_compliance": sla_compliance,
            "ai_resolution_pct": ai_pct,
            "escalation_rate": esc_rate,
            "avg_resolution_minutes": avg_minutes,
        }

    async def get_trends(self, db) -> dict:
        now = datetime.now()
        daily_volume = []
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            start = int(datetime(day.year, day.month, day.day, 0, 0, 0).timestamp() * 1000)
            end = int(datetime(day.year, day.month, day.day, 23, 59, 59).timestamp() * 1000)
            count = await db.tickets.count_documents({"createdAt": {"$gte": start, "$lte": end}})
            daily_volume.append({
                "date": day.strftime("%a"),
                "full_date": day.strftime("%Y-%m-%d"),
                "count": count,
            })

        category_trends = []
        for cat in ["software", "hardware", "access", "network", "other"]:
            week_start = int((now - timedelta(days=7)).timestamp() * 1000)
            count = await db.tickets.count_documents({
                "category": cat,
                "createdAt": {"$gte": week_start}
            })
            category_trends.append({"category": cat, "count": count})

        spike_alerts = await self._detect_spikes(db, daily_volume)

        return {
            "daily_volume": daily_volume,
            "category_trends": category_trends,
            "spike_alerts": spike_alerts,
        }

    async def get_trend_intelligence(self, db) -> dict:
        now = datetime.now()

        this_week_start = int((now - timedelta(days=7)).timestamp() * 1000)
        last_week_start = int((now - timedelta(days=14)).timestamp() * 1000)

        this_week = await db.tickets.count_documents({"createdAt": {"$gte": this_week_start}})
        last_week = await db.tickets.count_documents({
            "createdAt": {"$gte": last_week_start, "$lt": this_week_start}
        })

        pct_change = 0
        if last_week > 0:
            pct_change = round(((this_week - last_week) / last_week) * 100)

        recurring = await self._find_recurring(db, now)
        anomalies = await self._find_anomalies(db, now)

        heatmap = await self._build_heatmap(db, now)

        return {
            "week_comparison": {
                "this_week": this_week,
                "last_week": last_week,
                "pct_change": pct_change,
                "trend": "up" if pct_change > 0 else "down" if pct_change < 0 else "stable",
            },
            "recurring_issues": recurring,
            "anomalies": anomalies,
            "heatmap": heatmap,
        }

    async def _detect_spikes(self, db, daily_volume: list) -> list:
        counts = [d["count"] for d in daily_volume]
        if len(counts) < 3:
            return []

        rolling_avg = sum(counts[:-1]) / len(counts[:-1])
        today_count = counts[-1]
        alerts = []
        if rolling_avg > 0 and today_count >= rolling_avg * SPIKE_MULTIPLIER:
            alerts.append({
                "type": "volume_spike",
                "message": f"Today's ticket volume ({today_count}) is {round(today_count/rolling_avg, 1)}× the 7-day average",
                "severity": "high" if today_count >= rolling_avg * 3 else "medium",
            })
        return alerts

    async def _find_recurring(self, db, now: datetime) -> list:
        week_start = int((now - timedelta(days=7)).timestamp() * 1000)
        recurring = []
        for cat in ["software", "hardware", "access", "network", "other"]:
            count = await db.tickets.count_documents({
                "category": cat,
                "createdAt": {"$gte": week_start}
            })
            if count >= RECURRING_THRESHOLD:
                recurring.append({
                    "category": cat,
                    "count": count,
                    "label": f"{cat.capitalize()} issues",
                })
        return sorted(recurring, key=lambda x: x["count"], reverse=True)[:5]

    async def _find_anomalies(self, db, now: datetime) -> list:
        anomalies = []
        hour_start = int((now - timedelta(hours=1)).timestamp() * 1000)
        high_priority = await db.tickets.count_documents({
            "priority": {"$in": ["critical", "high"]},
            "createdAt": {"$gte": hour_start}
        })
        if high_priority >= 3:
            anomalies.append({
                "type": "high_priority_surge",
                "message": f"{high_priority} high-priority tickets in the last hour",
                "severity": "high",
            })
        return anomalies

    async def _build_heatmap(self, db, now: datetime) -> list:
        heatmap = []
        categories = ["software", "hardware", "access", "network", "other"]
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            start = int(datetime(day.year, day.month, day.day, 0, 0, 0).timestamp() * 1000)
            end = int(datetime(day.year, day.month, day.day, 23, 59, 59).timestamp() * 1000)
            row = {"day": day.strftime("%a")}
            for cat in categories:
                row[cat] = await db.tickets.count_documents({
                    "category": cat,
                    "createdAt": {"$gte": start, "$lte": end}
                })
            heatmap.append(row)
        return heatmap