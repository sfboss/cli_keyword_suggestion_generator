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
keywords generate "running shoes" --source-config examples/notebook-sources.yaml --output keywords.jsonl
keywords generate "running shoes" --source-config examples/sources.yaml --output unused.jsonl --dry-run
```

Source definitions use `{seed}` and other context placeholders. Secrets use `{env:VARIABLE_NAME}` and are redacted from dry-run output. Only GET requests are supported in this first deterministic collector increment.

`examples/notebook-sources.yaml` contains the 64 unkeyed suggestion endpoints recovered from the
endpoint-testing notebooks. During collection, the CLI renders one in-place Rich status table and
writes endpoint initialization, success, and failure records to `.keyword-generator/keywords.log`.
Endpoint health is customizable in the ConfigObj-compatible
`.keyword-generator/source-health.ini`; a source is automatically deprecated after ten consecutive
non-200 responses and a later successful health record re-enables it.

## Development

```bash
pytest
ruff check .
```
