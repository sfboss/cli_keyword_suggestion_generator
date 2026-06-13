import json

import pytest
from typer.testing import CliRunner

from keyword_generator.cli import app
from keyword_generator.collectors.parsers import parse_keywords
from keyword_generator.collectors.request_builder import plan_request, sanitized_request
from keyword_generator.models import ParserDefinition, ParserType, RawKeyword, SourceDefinition
from keyword_generator.processors.deduplicate import deduplicate


def source() -> SourceDefinition:
    return SourceDefinition.model_validate({"id": "suggest", "name": "Suggest", "request": {"url": "https://example.test", "query": {"q": "{seed}"}, "headers": {"Authorization": "Bearer {env:TOKEN}"}}, "parser": {"type": "json_path", "expression": "$.suggestions[*].phrase"}})


def test_request_planning_is_stable_and_redacts(monkeypatch):
    monkeypatch.setenv("TOKEN", "secret")
    first = plan_request(source(), "Shoes")
    assert first.request_id == plan_request(source(), "Shoes").request_id
    assert sanitized_request(first)["headers"]["Authorization"] == "[REDACTED]"


def test_json_parser_and_transforms():
    parser = ParserDefinition(type=ParserType.json_path, expression="$.suggestions[*].phrase", transforms=["strip", "html_unescape"])
    assert parse_keywords(json.dumps({"suggestions": [{"phrase": " shoes &amp; boots "}]}), parser) == ["shoes & boots"]


def test_deduplication_unions_provenance():
    records = deduplicate([RawKeyword(phrase=" Café  Shoes ", source_id="a", seed="cafe", request_id="1"), RawKeyword(phrase="café shoes", source_id="b", seed="shoes", request_id="2")])
    assert len(records) == 1
    assert records[0].occurrences == 2
    assert records[0].source_ids == {"a", "b"}


def test_invalid_transform_fails():
    with pytest.raises(ValueError, match="unsupported parser transform"):
        parse_keywords("value", ParserDefinition(type=ParserType.text, transforms=["eval"]))


def test_cli_dry_run_resolves_default_template_context(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "suggest",
                        "name": "Suggest",
                        "request": {
                            "url": "https://example.test/{market}",
                            "query": {"q": "{query}", "language": "{language}"},
                        },
                        "parser": {"type": "generic"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "generate",
            "email marketing",
            "--source-config",
            str(config_path),
            "--output",
            str(tmp_path / "email-marketing-keywords.jsonl"),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    request = json.loads(result.stdout)["requests"][0]
    assert request["url"] == "https://example.test/en-us"
    assert request["query"] == {"q": "email marketing", "language": "en"}
