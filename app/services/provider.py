import asyncio
import random
from typing import Dict, Any, Optional, Callable, Awaitable
import functools
import logging

logger = logging.getLogger(__name__)

# Simple async retry decorator with exponential backoff
def async_retry(
    tries: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    allowed_exceptions: tuple = (Exception,),
):
    def decorator(func: Callable[..., Awaitable]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _tries = tries
            _delay = delay
            while _tries > 1:
                try:
                    return await func(*args, **kwargs)
                except allowed_exceptions as e:
                    logger.warning("Provider call failed, will retry: %s; tries_left=%s", e, _tries - 1)
                    await asyncio.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
            # final attempt
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class MockProvider:
    async def _analyze(self, text: str) -> Dict[str, Any]:
        # deterministic but simple analysis
        t = text.lower()

        if "vpn" in t or "error 800" in t:
            category = "Network"
        elif "payment" in t or "billing" in t or "charge" in t:
            category = "Billing"
        elif "login" in t or "mfa" in t:
            category = "Login"
        elif "slow" in t or "latency" in t or "delay" in t:
            category = "Performance"
        else:
            category = "Bug"

        if any(k in t for k in ["crash", "down", "outage"]):
            severity = "Critical"
        elif any(k in t for k in ["cannot", "can't", "not working", "error"]):
            severity = "High"
        elif "slow" in t:
            severity = "Medium"
        else:
            severity = "Low"

        # simple key entities: pick up to 3 words longer than 3 chars
        key_entities = [w.strip(".,") for w in t.split() if len(w.strip(".,") ) > 4][:3]

        return {
            "summary": text.strip()[:200],
            "category": category,
            "severity": severity,
            "key_entities": key_entities,
            "reasoning": f"Detected category '{category}' from words {key_entities}"
        }

    @async_retry(tries=3, delay=0.3, backoff=2.0)
    async def analyze(self, text: str) -> Dict[str, Any]:
        # Simulate slight latency and occasional transient failure
        await asyncio.sleep(0.05 + random.random() * 0.05)
        # Simulate transient error randomly (very rare)
        if random.random() < 0.02:
            raise RuntimeError("Transient mock provider error")
        return await self._analyze(text)

# Provider factory - if you add Gemini/Groq clients, wrap them similarly
def get_provider():
    return MockProvider()
