import asyncio
import logging
from collections.abc import Callable

import httpx

from ..models import PlannedRequest, RawKeyword, SourceDefinition
from .parsers import parse_keywords
from ..runtime.source_health import SourceHealthStore

EventCallback = Callable[[str, str, int | None, int], None]


async def collect(requests: list[PlannedRequest], sources: dict[str, SourceDefinition], concurrency: int = 10, health: SourceHealthStore | None = None, event: EventCallback | None = None) -> tuple[list[RawKeyword], list[str]]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[RawKeyword] = []
    errors: list[str] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def fetch(request: PlannedRequest) -> None:
            async with semaphore:
                logging.getLogger("keyword_generator.sources").info("source_init source=%s request=%s", request.source_id, request.request_id)
                if event:
                    event(request.source_id, "running", None, 0)
                try:
                    response = await client.get(request.url, params=request.query, headers=request.headers, timeout=request.timeout_seconds)
                    response.raise_for_status()
                    phrases = parse_keywords(response.text, sources[request.source_id].parser)
                    for phrase in phrases:
                        results.append(RawKeyword(phrase=phrase, source_id=request.source_id, seed=request.seed, request_id=request.request_id))
                    if health:
                        health.record(request.source_id, response.status_code, True)
                    logging.getLogger("keyword_generator.sources").info("source_success source=%s status=%s results=%s", request.source_id, response.status_code, len(phrases))
                    if event:
                        event(request.source_id, "success", response.status_code, len(phrases))
                except Exception as exc:
                    errors.append(f"{request.source_id}/{request.request_id}: {type(exc).__name__}: {exc}")
                    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                    deprecated = health.record(request.source_id, status, False) if health else False
                    logging.getLogger("keyword_generator.sources").warning("source_failure source=%s status=%s deprecated=%s error=%s", request.source_id, status, deprecated, exc)
                    if event:
                        event(request.source_id, "deprecated" if deprecated else "failed", status, 0)
        await asyncio.gather(*(fetch(request) for request in requests))
    return results, errors
