# Keyword Suggestion Generator

A deterministic, provenance-preserving keyword research CLI. The initial collector supports validated YAML/JSON GET-source definitions, stable request planning, secret-safe dry runs, concurrent collection with partial failures, source-specific JSON/HTML/text/CSV/regex parsing, normalization, exact deduplication, and CSV/JSON/JSONL export.

## Install

```bash
python -m pip install -e '.[test]'
```

## Use

```bash
keywords config validate examples/sources.yaml
keywords generate "running shoes" --source-config examples/sources.yaml --output keywords.jsonl
keywords generate "running shoes" --source-config examples/sources.yaml --output unused.jsonl --dry-run
```

Source definitions use `{seed}` and other context placeholders. Secrets use `{env:VARIABLE_NAME}` and are redacted from dry-run output. Only GET requests are supported in this first deterministic collector increment.

## Development

```bash
pytest
ruff check .
```
