import asyncio
from models.model_loader import ModelLoader

CATEGORY_LABELS = ["software", "hardware", "access", "network", "other"]
PRIORITY_LABELS = ["critical", "high", "medium", "low"]

INTENT_MAP = {
    "software": "Software Issue / Application Error",
    "hardware": "Hardware Malfunction / Device Problem",
    "access": "Access & Authentication Request",
    "network": "Network / Connectivity Issue",
    "other": "General IT Support Request",
}


class TicketAnalyzerAgent:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader

    async def run(self, title: str, description: str) -> dict:
        text = f"{title}. {description}".strip()
        loop = asyncio.get_event_loop()

        cat_result, pri_result = await asyncio.gather(
            loop.run_in_executor(None, self._classify, text, CATEGORY_LABELS),
            loop.run_in_executor(None, self._classify, text, PRIORITY_LABELS),
        )

        category = cat_result["labels"][0]
        confidence = round(cat_result["scores"][0], 3)
        priority = pri_result["labels"][0]

        return {
            "intent": INTENT_MAP.get(category, "General IT Support Request"),
            "summary": self._summarize(description),
            "suggestedPriority": priority,
            "suggestedCategory": category,
            "confidenceScore": confidence,
        }

    def _classify(self, text: str, labels: list) -> dict:
        return self.model_loader.classifier(text, labels)

    def _summarize(self, description: str) -> str:
        sentences = description.replace("\n", ". ").split(". ")
        first = sentences[0].strip() if sentences else description
        return (first[:197] + "...") if len(first) > 200 else first
