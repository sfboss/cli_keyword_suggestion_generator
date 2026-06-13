import json

from keyword_generator.collectors.parsers import parse_keywords
from keyword_generator.models import ParserDefinition, ParserType
from keyword_generator.runtime.source_health import SourceHealthStore


def test_generic_parser_extracts_nested_suggestions():
    body = json.dumps({"suggestions": [{"value": "running shoes"}, {"value": "running trainers"}]})
    parser = ParserDefinition(type=ParserType.generic)
    assert parse_keywords(body, parser) == ["running shoes", "running trainers"]


def test_source_health_deprecates_after_ten_consecutive_non_200(tmp_path):
    path = tmp_path / "health.ini"
    health = SourceHealthStore(path)
    for _ in range(9):
        assert not health.record("example", 503, False)
    assert health.record("example", 503, False)
    assert SourceHealthStore(path).is_deprecated("example")
    assert not health.record("example", 200, True)
    assert not SourceHealthStore(path).is_deprecated("example")
