from pathlib import Path

from .collectors.engine import collect
from .collectors.request_builder import plan_request
from .config import load_source_config
from .exporters.files import export_records
from .models import KeywordRecord
from .processors.deduplicate import deduplicate
from .runtime.source_health import SourceHealthStore


async def generate(seeds: list[str], source_config: Path, output: Path, format: str, concurrency: int = 10, health_path: Path | None = None, event=None) -> tuple[list[KeywordRecord], list[str]]:
    config = load_source_config(source_config)
    health = SourceHealthStore(health_path or Path(".keyword-generator/source-health.ini"))
    sources = {source.id: source for source in config.sources if source.enabled and not source.deprecated and not health.is_deprecated(source.id)}
    context = {"language": "en", "lang": "en", "country": "US", "market": "en-us", "cp": "1", "query": ""}
    requests = [plan_request(source, seed, {**context, "query": seed}) for seed in seeds for source in sources.values()]
    raw, errors = await collect(requests, sources, concurrency, health, event)
    records = deduplicate(raw)
    export_records(records, output, format)
    return records, errors
