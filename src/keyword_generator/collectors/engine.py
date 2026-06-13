import asyncio

import httpx

from ..models import PlannedRequest, RawKeyword, SourceDefinition
from .parsers import parse_keywords


async def collect(requests: list[PlannedRequest], sources: dict[str, SourceDefinition], concurrency: int = 10) -> tuple[list[RawKeyword], list[str]]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[RawKeyword] = []
    errors: list[str] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def fetch(request: PlannedRequest) -> None:
            async with semaphore:
                try:
                    response = await client.get(request.url, params=request.query, headers=request.headers, timeout=request.timeout_seconds)
                    response.raise_for_status()
                    for phrase in parse_keywords(response.text, sources[request.source_id].parser):
                        results.append(RawKeyword(phrase=phrase, source_id=request.source_id, seed=request.seed, request_id=request.request_id))
                except Exception as exc:
                    errors.append(f"{request.source_id}/{request.request_id}: {type(exc).__name__}: {exc}")
        await asyncio.gather(*(fetch(request) for request in requests))
    return results, errors
