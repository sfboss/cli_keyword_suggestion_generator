# Keyword Suggestion Generator

A deterministic, provenance-preserving keyword research CLI. The initial collector supports validated YAML/JSON GET-source definitions, stable request planning, secret-safe dry runs, concurrent collection with partial failures, source-specific JSON/HTML/text/CSV/regex parsing, normalization, exact deduplication, and CSV/JSON/JSONL export.

## Install

```bash
python -m pip install -e '.[test]'
```

## Quick start

```bash
keywords config validate examples/notebook-sources.yaml
keywords generate "running shoes" \
  --source-config examples/notebook-sources.yaml \
  --output running-shoes-keywords.jsonl
```

The generate command above runs the working, unkeyed suggestion sources recovered from the
notebooks and writes the deduplicated results to `running-shoes-keywords.jsonl`. Output files are
never overwritten.

## Command reference

```text
Usage: keywords [OPTIONS] COMMAND [ARGS]...

Deterministic, provenance-preserving keyword research.

Commands:
  generate          Collect and export keyword suggestions.
  config validate   Validate a YAML or JSON source configuration.
```

```text
Usage: keywords generate [OPTIONS] SEEDS...

Arguments:
  SEEDS...                         One or more seed keywords. [required]

Options:
  --source-config PATH             YAML or JSON source configuration. [required]
  --output PATH                    Destination output file. [required]
  --format [jsonl|json|csv]        Export format. [default: jsonl]
  --concurrency INTEGER            Maximum concurrent requests. [default: 10]
  --health-file PATH               Persistent endpoint health INI file.
  --log-file PATH                  Endpoint activity log file.
  --dry-run                        Print the sanitized request plan without collecting.
  --color / --no-color             Force or disable colored terminal output.
  --help                           Show command help.
```

## Example commands

Collect one keyword as JSONL:

```bash
keywords generate "running shoes" \
  --source-config examples/notebook-sources.yaml \
  --output running-shoes-keywords.jsonl
```

Collect multiple keywords as CSV:

```bash
keywords generate "coffee maker" "espresso machine" \
  --source-config examples/notebook-sources.yaml \
  --format csv \
  --output coffee-maker-espresso-machine-keywords.csv
```

Preview the sanitized request plan without making requests:

```bash
keywords generate "email marketing" \
  --source-config examples/notebook-sources.yaml \
  --output email-marketing-keywords.jsonl \
  --dry-run
```

Use custom endpoint health and log files:

```bash
keywords generate "local seo" \
  --source-config examples/notebook-sources.yaml \
  --output local-seo-keywords.jsonl \
  --health-file local-seo-source-health.ini \
  --log-file local-seo-endpoints.log
```

Source definitions use `{seed}` and other context placeholders. Secrets use `{env:VARIABLE_NAME}` and are redacted from dry-run output. Only GET requests are supported in this first deterministic collector increment.

`examples/notebook-sources.yaml` contains the 64 unkeyed suggestion endpoints recovered from the
endpoint-testing notebooks. During collection, the CLI renders one bounded, colored Rich dashboard
in the terminal's alternate screen. It shows active and recent sources while writing full endpoint
initialization, success, and failure records to `.keyword-generator/keywords.log`. The completion
view reports a compact failure count instead of printing every source error.
Endpoint health is customizable in the ConfigObj-compatible
`.keyword-generator/source-health.ini`; a source is automatically deprecated after ten consecutive
non-200 responses and a later successful health record re-enables it.
Color is automatic in a compatible terminal, respects `NO_COLOR`, and can be forced with `--color`.

`examples/sources.yaml` is a small source-configuration example that uses a placeholder
`api.example.com` endpoint; use `examples/notebook-sources.yaml` for runnable collection examples.

## Development

```bash
pytest -q
ruff check .
```
