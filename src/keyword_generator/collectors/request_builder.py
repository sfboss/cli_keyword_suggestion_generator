from __future__ import annotations

import hashlib
import os
import re
from typing import Mapping

from ..models import PlannedRequest, SourceDefinition

_TEMPLATE = re.compile(r"\{([^{}]+)\}")
_SECRET_HEADERS = {"authorization", "proxy-authorization", "x-api-key", "api-key"}


def resolve_template(value: str, context: Mapping[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key.startswith("env:"):
            name = key[4:]
            if name not in os.environ:
                raise ValueError(f"missing environment variable: {name}")
            return os.environ[name]
        if key not in context:
            raise ValueError(f"unknown template value: {key}")
        return context[key]

    return _TEMPLATE.sub(replace, value)


def plan_request(source: SourceDefinition, seed: str, context: Mapping[str, str] | None = None) -> PlannedRequest:
    values = {"seed": seed, **(context or {})}
    url = resolve_template(source.request.url, values)
    query = {key: resolve_template(value, values) for key, value in source.request.query.items()}
    headers = {key: resolve_template(value, values) for key, value in source.request.headers.items()}
    stable = f"{source.id}\0{seed}\0{url}\0{sorted(query.items())}"
    request_id = hashlib.sha256(stable.encode()).hexdigest()[:20]
    return PlannedRequest(request_id=request_id, source_id=source.id, seed=seed, url=url, query=query, headers=headers, timeout_seconds=source.request.timeout_seconds)


def sanitized_request(request: PlannedRequest) -> dict[str, object]:
    data = request.model_dump()
    data["headers"] = {key: "[REDACTED]" if key.lower() in _SECRET_HEADERS else value for key, value in request.headers.items()}
    return data
