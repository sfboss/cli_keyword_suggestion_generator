# AGENTS.md

## Mission

Build the definitive keyword research CLI: a fast, configurable Python application that gathers keyword ideas from many HTTP GET sources, parses them through source-specific rules, normalizes and deduplicates them, optionally enriches them with SEO, Google Ads, and AI-generated data, scores them, and exports useful datasets.

The CLI must work equally well in:

- Scripted, non-interactive automation.
- A cohesive interactive terminal workflow.
- Small local runs and large resumable research jobs.

Treat this document as the product specification and the default engineering guidance for all work in this repository.

## Product Principles

1. **Deterministic core, optional augmentation.** Collection, parsing, normalization, deduplication, filtering, and scoring must remain useful without AI or paid APIs.
2. **Configuration over source-specific branching.** Most keyword sources should be expressible as data: a GET request template plus a parser definition.
3. **Provenance is never lost.** Every keyword must retain the sources, seed terms, request IDs, and transformations that produced it.
4. **Interactive and non-interactive modes share one engine.** The interactive UI only gathers options and renders progress; it must not contain pipeline logic.
5. **Useful partial results beat failed runs.** Cache requests, checkpoint stages, isolate source failures, and allow resume.
6. **Outputs are analysis-ready.** Exports should be stable, documented, and easy to consume as CSV, JSONL, JSON, SQLite, or stdout.
7. **Terminal output is intentional.** Do not stack banners, menus, progress displays, and logs indefinitely. Render a single current scene whenever possible.

## Recommended Technology

- Python 3.12+
- `typer` for commands, options, shell completion, and non-interactive CLI behavior
- `pydantic` and `pydantic-settings` for validated models and configuration
- `httpx` with `asyncio` for concurrent GET requests
- `tenacity` for bounded retries and backoff
- `InquirerPy` for interactive menus, forms, confirmations, and fuzzy selection
- `rich` for styled stdout, progress, status, panels, logs, and live tables
- `orjson` for large JSON/JSONL data where useful
- `jsonpath-ng` for JSON extraction
- `beautifulsoup4` or `selectolax` for HTML parsing
- `pyyaml` for YAML configuration
- `rapidfuzz` for optional near-duplicate grouping
- `aiosqlite` or SQLAlchemy for the run cache and resumable state
- `pytest`, `pytest-asyncio`, `respx`, and `hypothesis` for tests
- `ruff` and `mypy` for linting, formatting, and type checking

Keep provider SDKs optional. Install AI and Google Ads dependencies through extras so the base collector remains lightweight.

## Target Project Layout

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── src/
│   └── keyword_generator/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── pipeline.py
│       ├── collectors/
│       │   ├── engine.py
│       │   ├── request_builder.py
│       │   └── parsers.py
│       ├── processors/
│       │   ├── normalize.py
│       │   ├── deduplicate.py
│       │   ├── filter.py
│       │   ├── cluster.py
│       │   └── score.py
│       ├── enrichers/
│       │   ├── base.py
│       │   ├── ai.py
│       │   ├── google_ads.py
│       │   ├── serp.py
│       │   └── seo.py
│       ├── exporters/
│       │   ├── csv.py
│       │   ├── json.py
│       │   ├── jsonl.py
│       │   ├── sqlite.py
│       │   └── stdout.py
│       ├── runtime/
│       │   ├── cache.py
│       │   ├── events.py
│       │   ├── rate_limit.py
│       │   └── run_store.py
│       └── ui/
│           ├── app.py
│           ├── banner.py
│           ├── scenes.py
│           ├── prompts.py
│           └── tables.py
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── examples/
    ├── sources.yaml
    └── project.yaml
```

Do not create every module before it earns its place. Maintain these ownership boundaries as the application grows.

## Core User Journeys

### One-command research

```bash
keywords generate "running shoes" \
  --source-config examples/sources.yaml \
  --expand alphabet,suggestions,questions \
  --enrich seo,google-ads \
  --cluster \
  --score balanced \
  --output results.csv
```

### Multiple seeds from files and stdin

```bash
keywords generate --seed-file seeds.txt --output keywords.jsonl
cat seeds.txt | keywords generate --stdin --format jsonl
```

### Interactive application

```bash
keywords
keywords interactive
```

### Resume a partially completed run

```bash
keywords resume <run-id>
```

### Validate configuration without making requests

```bash
keywords config validate project.yaml
keywords sources test suggestions-source --seed "running shoes"
```

## CLI Surface

The executable should be `keywords`. Commands and options must support shell completion and useful `--help` output.

### Primary commands

- `keywords generate [SEEDS...]`: execute the complete configured pipeline.
- `keywords interactive`: launch the guided terminal application.
- `keywords resume RUN_ID`: continue from the last durable checkpoint.
- `keywords inspect RUN_ID`: show configuration, stage status, errors, counts, timing, and output paths.
- `keywords export RUN_ID`: re-export a completed or partial run without recollecting.
- `keywords sources list`: display configured and built-in sources.
- `keywords sources test SOURCE_ID`: make a sample request and preview parsed keywords.
- `keywords config init`: generate a documented starter configuration.
- `keywords config validate PATH`: validate configuration and referenced secrets.
- `keywords cache stats|clear|prune`: inspect and manage cached responses.
- `keywords providers list|check`: show optional enrichment-provider availability.

### Important `generate` options

- Seeds: `--seed`, `--seed-file`, `--stdin`
- Configuration: `--config`, `--source-config`, `--profile`
- Sources: `--source`, `--exclude-source`, `--all-sources`
- Expansion: `--expand`, `--alphabet`, `--prefixes`, `--suffixes`, `--depth`, `--max-generated-seeds`
- Locales: `--language`, `--country`, `--location`
- Collection: `--concurrency`, `--requests-per-second`, `--timeout`, `--retries`, `--cache-ttl`, `--refresh`
- Processing: `--normalize`, `--dedupe-mode`, `--near-duplicate-threshold`, `--include`, `--exclude`, `--min-words`, `--max-words`
- Enrichment: `--enrich`, `--ai-provider`, `--ai-model`, `--google-ads-customer-id`, `--serp-provider`
- Analysis: `--intent`, `--cluster`, `--cluster-method`, `--score`, `--score-config`
- Output: `--output`, `--format`, `--fields`, `--sort`, `--limit`, `--overwrite`
- Runtime: `--interactive`, `--dry-run`, `--resume`, `--no-cache`, `--quiet`, `--verbose`, `--debug`, `--no-color`, `--json-events`

Boolean options should have explicit inverse forms where ambiguity matters, such as `--cache/--no-cache`.

## Pipeline

Implement the pipeline as independently testable stages:

```text
inputs
  -> seed preparation and expansion
  -> request planning
  -> concurrent GET collection
  -> source parsing
  -> normalization
  -> exact deduplication
  -> filtering
  -> optional enrichment
  -> optional near-duplicate grouping and topic clustering
  -> scoring and ranking
  -> export
```

Each stage must:

- Accept and return typed models.
- Emit structured progress events.
- Record counts, duration, warnings, and errors.
- Be independently skippable when its output is already checkpointed.
- Avoid silently discarding records.

Failures in one source or optional enricher should be recorded and surfaced without automatically failing the entire run. Fail the run only when required inputs or required stages cannot produce a valid result.

## Request Source Configuration

Users must be able to pass an array of GET request definitions through project configuration or a dedicated source file. YAML and JSON should both be accepted.

Example:

```yaml
version: 1
sources:
  - id: example-suggestions
    name: Example Suggestions
    enabled: true
    request:
      method: GET
      url: "https://api.example.com/suggest"
      query:
        q: "{seed}"
        language: "{language}"
        country: "{country}"
      headers:
        Accept: "application/json"
        Authorization: "Bearer {env:EXAMPLE_API_KEY}"
      timeout_seconds: 10
      rate_limit:
        requests: 5
        per_seconds: 1
      cache_ttl_seconds: 86400
    parser:
      type: jsonpath
      expression: "$.suggestions[*].phrase"
      value_field: null
      transforms:
        - strip
        - html_unescape
    pagination:
      type: query
      parameter: page
      start: 1
      max_pages: 3
      stop_when_empty: true
    tags: [suggestions, free]
```

### Request definition requirements

- Only `GET` is in scope for the first implementation, but models should permit future HTTP methods without redesigning the pipeline.
- Template values may reference the seed, expansion, locale, pagination values, configuration values, and environment variables.
- Secrets must come from environment variables, secret stores, or provider configuration. Never persist resolved secrets in run metadata or logs.
- Supported parser types should include:
  - JSONPath extraction
  - JSON list or object path extraction
  - HTML CSS selector extraction
  - HTML attribute extraction
  - line-delimited text
  - CSV column extraction
  - regex capture groups, only when structured parsing is unsuitable
- A parser may emit only a phrase or a phrase plus source-provided metadata.
- Parser transforms must be named, ordered, validated functions. Do not allow arbitrary code execution in configuration.
- Config validation must catch missing templates, unsupported parser types, invalid expressions, duplicate source IDs, and unsafe secret placement before a run.
- Request logs must redact credentials and sensitive query parameters.

### Request planning

Before collection, compile seeds, expansions, sources, locales, and pages into a request plan with stable request IDs. A dry run should show:

- Estimated request count.
- Enabled sources and expansions.
- Estimated provider cost where known.
- Missing credentials.
- Rate-limit and concurrency settings.
- Output and checkpoint locations.

Guard against accidental request explosions with configurable hard limits and an interactive confirmation when the estimate exceeds a threshold.

## Seed Expansion

Provide configurable, bounded expansion strategies:

- Original seed.
- Alphabet expansion: `seed a` through `seed z`, optionally prefixes.
- Number expansion.
- Question modifiers: who, what, when, where, why, how, can, should, best.
- Commercial modifiers: buy, price, discount, near me, review, alternative, versus.
- User-supplied prefix and suffix lists.
- Source-returned recursive expansion with explicit maximum depth and maximum generated seeds.
- Optional AI expansion.

Every expanded seed must record its parent seed, expansion strategy, and depth.

## Keyword Data Model

Use a canonical model similar to:

```python
class KeywordRecord(BaseModel):
    keyword_id: str
    phrase: str
    normalized_phrase: str
    display_phrase: str
    language: str | None
    country: str | None
    seed_terms: set[str]
    expansions: set[str]
    source_ids: set[str]
    request_ids: set[str]
    first_seen_at: datetime
    occurrences: int
    source_metadata: dict[str, object]
    seo: SeoMetrics | None
    ads: AdsMetrics | None
    ai: AiAnnotations | None
    intent: list[str]
    entities: list[str]
    cluster_id: str | None
    score: float | None
    score_components: dict[str, float]
    warnings: list[str]
```

Sets may be serialized as stable sorted lists. Provider-specific raw data should be retained in namespaced metadata only when enabled, because it may be large.

## Normalization and Deduplication

Deduplication must be deterministic and auditable.

Default normalization should:

1. Decode and normalize Unicode consistently.
2. HTML-unescape and trim surrounding whitespace.
3. Collapse repeated internal whitespace.
4. Normalize case for comparison while preserving a display phrase.
5. Standardize punctuation variants conservatively.
6. Preserve meaningful numbers, apostrophes, hyphens, and non-English text.

Do not stem, singularize, remove stop words, or reorder words during exact deduplication. Those operations may incorrectly merge different search intent.

Exact duplicates merge into one record and union their provenance. Optional near-duplicate grouping and semantic clustering happen later and must not destroy the original records.

Support configurable dedupe scopes:

- Global normalized phrase.
- Phrase plus language.
- Phrase plus language and country.

Generate stable keyword IDs from the selected dedupe key.

## Enrichment

Enrichment is optional, pluggable, cacheable, and cost-aware. Each enricher declares required credentials, supported locales, batching behavior, estimated cost, and produced fields.

### SEO enrichment

Support provider adapters that can add fields such as:

- Monthly search volume.
- Keyword difficulty or competition.
- CPC and paid competition.
- Trend history and seasonality.
- SERP result count and SERP features.
- Ranking-domain or competitor data.
- Search intent.

Do not imply that metrics from different providers are directly equivalent. Preserve provider name and observation date.

### Google Ads enrichment

Use the current Google Ads API rather than legacy AdWords APIs, while permitting `google-ads` and `adwords` as user-facing aliases.

Support:

- Keyword ideas and historical metrics.
- Average monthly searches.
- Competition and competition index.
- Low and high top-of-page bid ranges.
- Monthly volume history where available.
- Location, language, network, and customer account configuration.

Batch requests where supported, respect quotas, cache results, and make expected API requirements clear. Never log OAuth secrets, developer tokens, refresh tokens, or customer credentials.

### AI augmentation

AI must never be required for the core pipeline. Support provider adapters and structured outputs for:

- Additional keyword ideas.
- Intent classification.
- Funnel-stage classification.
- Topic labels and semantic clusters.
- Entity and audience extraction.
- Suggested negatives.
- Content type, title, and brief suggestions.
- Explanations for score or opportunity.

AI calls must use validated structured output, batch keywords, cache by model and prompt version, record model/provider, estimate cost before execution, and allow a hard spending limit. AI-generated keywords must be visibly marked with AI provenance and pass through the same normalization and deduplication pipeline.

### Additional useful enrichers

- Live SERP snapshots and SERP feature detection.
- Search trend data.
- First-party Search Console data.
- Competitor URL and content-gap analysis.
- Domain rankability or topical-authority inputs.
- User-provided CSV lookup joins.

Keep these behind adapters; do not couple the core model to one vendor.

## Filtering, Clustering, and Scoring

Filtering should support word count, regex, required terms, excluded terms, source, locale, intent, metric ranges, and negative keyword lists.

Clustering options may include:

- Lexical similarity.
- Shared n-grams.
- SERP overlap.
- Embedding similarity.
- AI-assisted topic labeling.

Scoring must be transparent. Supply profiles such as:

- `volume`: prioritizes demand.
- `low-competition`: prioritizes easier opportunities.
- `commercial`: prioritizes CPC and transactional intent.
- `content-gap`: prioritizes competitor gaps.
- `balanced`: configurable weighted combination.

Every score must include component values and weights. Missing metrics must be handled explicitly instead of silently treated as zero.

## Interactive Terminal UX

The interactive UI must use `InquirerPy` and `rich`. It is a guided front end to the same commands and pipeline used by non-interactive mode.

### Scene model

Treat every menu, form, confirmation, run dashboard, and result summary as a terminal **scene**.

For each new scene:

1. Stop any active Rich `Live` display.
2. Clear the terminal using the shared console abstraction.
3. Render the ASCII art banner once.
4. Render a concise breadcrumb and scene-specific context.
5. Render exactly one prompt flow, dashboard, or result view beneath it.

Prefer an alternate-screen session when the terminal and InquirerPy behavior are compatible. Otherwise, use `Console.clear()` and redraw. Do not emit repeated banners or old menus into scrollback during normal navigation.

Never run an InquirerPy prompt while a Rich `Live` context is active. Stop live rendering, clear/redraw the scene, then prompt.

### Banner

- On interactive startup, clear stdout and render a tasteful, compact ASCII art product name.
- Use a bundled ASCII banner or a small banner generator; startup must not depend on network access.
- Render it through Rich so color and style are centralized.
- Respect `NO_COLOR`, `--no-color`, non-TTY output, and narrow terminals.
- Use a short fallback title when the terminal is too narrow.

### Main menu

The main menu should contain:

- Start keyword research
- Resume a run
- Inspect previous runs
- Manage sources
- Configure enrichment providers
- Validate configuration
- Manage cache
- Help
- Exit

### Guided research flow

Use a cohesive sequence with sensible defaults:

```text
Main menu
  -> Seed input
  -> Locale and expansion choices
  -> Source selection
  -> Processing and filter choices
  -> Enrichment choices
  -> Output choices
  -> Cost/request estimate and confirmation
  -> Live run dashboard
  -> Results summary
  -> Export / inspect / run again / main menu
```

Every nested scene must consistently provide `Back`, `Main menu`, and `Exit` actions where appropriate. Back navigation edits the previous step without losing already entered values. Confirmation screens summarize choices before expensive work.

Keyboard interrupts should be handled cleanly:

- During prompts: confirm whether to return to the main menu or exit.
- During a run: offer cancel-and-save, continue, or force exit.
- Restore cursor visibility and terminal state on all exits.

### Live run dashboard

Use one Rich `Live` instance for the active run. Update its renderable in place rather than printing a new progress line for every event.

The dashboard should show:

- Current stage and elapsed time.
- Overall and stage progress.
- Requests planned/completed/failed/cached.
- Keywords parsed/normalized/unique/enriched.
- Active source status, rate limit, and recent errors.
- Estimated and actual paid-provider/AI cost.
- Current checkpoint and output path.

Keep a small bounded recent-event region, not an unbounded log. Detailed logs belong in a run log file and are displayed only in verbose/debug mode.

On completion, stop the live display and render a clean results-summary scene. Avoid leaving a full history of intermediate table states in stdout.

### Non-interactive output behavior

- Data written to stdout must never be mixed with decorative output.
- Send diagnostics and progress to stderr.
- Disable interactive prompts and live rendering when stdout/stderr are not TTYs.
- `--quiet` emits only requested data and fatal errors.
- `--json-events` emits machine-readable progress events instead of Rich output.

## Runtime State, Caching, and Resume

Give every run a stable ID and store:

- Resolved non-secret configuration.
- Request plan and request status.
- Cached raw responses or references to them.
- Stage checkpoints.
- Structured events, warnings, and errors.
- Provider usage and estimated/actual cost.
- Export manifests.

Cache keys should include the sanitized request, parser/source version when relevant, and locale. Use TTLs and allow forced refresh. Writes must be atomic.

Resume must not repeat successful paid calls or completed requests unless the user explicitly requests refresh.

## Networking and Reliability

- Use bounded async concurrency and per-host/provider rate limits.
- Respect configured timeouts, retries, backoff, and `Retry-After`.
- Retry only errors likely to be transient.
- Cap response sizes and reject unexpectedly large payloads.
- Validate content type while allowing explicitly configured exceptions.
- Use a descriptive user agent.
- Redact secrets from exceptions and diagnostic output.
- Expose source failures with enough context to repair parser or request configuration.
- Follow provider terms, quotas, and applicable API requirements.

## Configuration Precedence

Use predictable precedence, highest first:

1. CLI options.
2. Explicit `--config`.
3. Project-local configuration.
4. User configuration.
5. Environment variables and `.env` for secrets/settings.
6. Application defaults.

Interactive choices should produce the same resolved configuration model as CLI arguments. Offer to save a reusable profile, but never save secrets into it.

## Exports

All exporters consume the same final typed records.

- CSV: flattened, stable columns suitable for spreadsheets.
- JSON: complete run metadata plus records.
- JSONL: one keyword record per line for streaming.
- SQLite: normalized tables for keywords, provenance, metrics, and runs.
- stdout: table for humans or CSV/JSONL for pipelines.

Exports must include an optional run manifest containing configuration, source versions, metric dates, stage counts, warnings, and field definitions.

Do not overwrite existing files without `--overwrite` or interactive confirmation.

## Observability

Pipeline components emit typed events rather than printing directly. Rendering and logging subscribe to those events.

Required event categories:

- Run and stage lifecycle.
- Request planned, started, retried, cached, completed, and failed.
- Parser warning and failure.
- Keyword counts after each processing stage.
- Enrichment batches and provider usage.
- Checkpoint and export completion.

Use human-readable log files by default and optionally structured JSON logs. Debug logs must remain secret-safe.

## Security and Privacy

- Never log, cache, export, or checkpoint resolved secrets.
- Redact sensitive headers and configurable query parameters.
- Require explicit opt-in before sending keywords or first-party data to AI providers.
- Clearly display which provider receives what data.
- Avoid arbitrary Python/code execution from configuration.
- Validate configured URLs and document the implications of requesting private-network URLs.
- Use safe file creation and avoid overwriting unrelated files.

## Testing Expectations

Tests should cover behavior, not just implementation details.

### Unit tests

- Template resolution and secret redaction.
- Each parser type and transform.
- Unicode-aware normalization.
- Exact deduplication and provenance union.
- Filters, scoring profiles, and missing metrics.
- Configuration precedence and validation.
- Event generation and checkpoint behavior.

### Integration tests

- Concurrent collection, rate limiting, retries, pagination, caching, and partial failures using mocked HTTP.
- Enrichment batching and provider failures using mocked adapters.
- Resume without repeating completed or paid work.
- Every exporter with stable fixtures.

### End-to-end tests

- Non-interactive generation from fixture sources to each output type.
- Interactive happy path, back navigation, cancellation, and terminal cleanup.
- Piped/non-TTY behavior with no decorative stdout contamination.

Never make live paid-provider calls in the default test suite. Mark optional live contract tests explicitly.

## Engineering Rules

- Keep domain logic independent of Typer, Rich, and InquirerPy.
- UI code may consume pipeline events but must not implement collection or processing logic.
- Collectors and enrichers use explicit adapter interfaces.
- Use typed models at module boundaries; avoid passing unvalidated dictionaries through the pipeline.
- Prefer structured parsers over regex or manual string slicing.
- Keep transformations deterministic and preserve raw provenance.
- Add dependencies only when they remove meaningful complexity.
- Add focused tests with every behavior change.
- Update README examples and command help when the user-facing CLI changes.
- Do not silently change export schemas; version them.

## Initial Delivery Milestones

### Milestone 1: Deterministic collector

- Typer CLI and validated YAML/JSON configuration.
- Array of GET source definitions.
- JSON, HTML, text, CSV, and regex parsers.
- Async collection, retries, rate limiting, caching, and request dry run.
- Normalization, exact deduplication, provenance, filtering.
- CSV, JSONL, and stdout exports.
- Unit and integration tests.

### Milestone 2: Interactive application

- InquirerPy guided flow.
- Rich ASCII banner, scene navigation, and clean terminal handling.
- Single in-place live dashboard.
- Saved profiles, run history, checkpoints, inspect, and resume.

### Milestone 3: Enrichment and analysis

- Google Ads adapter.
- Generic SEO and SERP provider interfaces with at least one adapter.
- AI provider interface with structured, batched augmentation.
- Cost estimation and hard limits.
- Transparent scoring and clustering.
- SQLite export.

### Milestone 4: Production hardening

- Shell completion and packaged executable.
- Performance tests and large-run streaming behavior.
- Provider contract tests.
- Polished docs, examples, error messages, and migration/versioning strategy.

## Definition of Done

A feature is complete when:

- It works through both the non-interactive engine and the interactive UI where applicable.
- Configuration and output behavior are documented.
- Failure paths and secret redaction are handled.
- Progress events and run metadata are recorded.
- Focused automated tests pass.
- Terminal output remains clean: no nested live displays, duplicated banners, runaway logs, or data mixed with decorative stdout.

