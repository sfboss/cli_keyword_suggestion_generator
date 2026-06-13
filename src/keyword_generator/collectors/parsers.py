from __future__ import annotations

import csv
import html
import io
import json
import re
from typing import Any

from bs4 import BeautifulSoup

from ..models import ParserDefinition, ParserType


def _transform(value: str, transforms: list[str]) -> str:
    functions = {"strip": str.strip, "lower": str.lower, "html_unescape": html.unescape}
    for name in transforms:
        if name not in functions:
            raise ValueError(f"unsupported parser transform: {name}")
        value = functions[name](value)
    return value


def _walk_json(value: Any, path: str) -> list[Any]:
    current = [value]
    for part in path.removeprefix("$.").split("."):
        many = part.endswith("[*]")
        key = part[:-3] if many else part
        next_values = []
        for item in current:
            found = item.get(key) if key and isinstance(item, dict) else item
            next_values.extend(found if many and isinstance(found, list) else [found])
        current = [item for item in next_values if item is not None]
    return current


def parse_keywords(body: str, parser: ParserDefinition) -> list[str]:
    expression = parser.expression or ""
    if parser.type == ParserType.json_path:
        values = _walk_json(json.loads(body), expression)
    elif parser.type == ParserType.html:
        nodes = BeautifulSoup(body, "html.parser").select(expression)
        values = [node.get(parser.attribute) if parser.attribute else node.get_text() for node in nodes]
    elif parser.type == ParserType.text:
        values = body.splitlines()
    elif parser.type == ParserType.csv:
        values = [row[expression] for row in csv.DictReader(io.StringIO(body)) if row.get(expression)]
    else:
        values = re.findall(expression, body)
    return [result for value in values if value is not None and (result := _transform(str(value), parser.transforms))]
