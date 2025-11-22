from app.services.provider import get_provider
from app.services.kb import KnowledgeBaseService
from app.schemas import TriageSchema, TriageResponse, KBEntry
import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)

class TriageAgent:
    def __init__(self, kb: KnowledgeBaseService, provider_timeout: float = 8.0):
        self.kb = kb
        self.provider = get_provider()
        self.provider_timeout = provider_timeout

    async def _analyze_safe(self, text: str) -> TriageSchema:
        """
        Call provider.analyze with timeout and convert to schema.
        Raises RuntimeError on failure.
        """
        try:
            coro = self.provider.analyze(text)
            raw = await asyncio.wait_for(coro, timeout=self.provider_timeout)
            # Validate via Pydantic
            return TriageSchema(**raw)
        except asyncio.TimeoutError:
            logger.exception("LLM/provider call timed out")
            raise RuntimeError("LLM provider timeout")
        except Exception as e:
            logger.exception("LLM/provider call failed: %s", e)
            raise RuntimeError("LLM provider failure")

    async def process(self, text: str) -> TriageResponse:
        # 1) Analyze with provider (wrapped for retries + timeout)
        analysis = await self._analyze_safe(text)

        # 2) Retrieve from KB
        query = f"{analysis.category} {' '.join(analysis.key_entities)}"
        hits: List[KBEntry] = self.kb.search(query)

        # 3) Decide known/new and suggested action
        known = len(hits) > 0
        if known:
            suggested = f"Attach KB article and respond to user.\nTop match: {hits[0].title}"
        else:
            suggested = "Ask customer for more logs or escalate to engineering."

        return TriageResponse(
            analysis=analysis,
            similar_issues=hits,
            suggested_action=suggested,
            known_issue=known
        )
