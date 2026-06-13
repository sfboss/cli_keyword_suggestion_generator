from pathlib import Path

from .collectors.engine import collect
from .collectors.request_builder import plan_request
from .config import load_source_config
from .exporters.files import export_records
from .models import KeywordRecord
from .processors.deduplicate import deduplicate


async def generate(seeds: list[str], source_config: Path, output: Path, format: str, concurrency: int = 10) -> tuple[list[KeywordRecord], list[str]]:
    config = load_source_config(source_config)
    sources = {source.id: source for source in config.sources if source.enabled}
    requests = [plan_request(source, seed) for seed in seeds for source in sources.values()]
    raw, errors = await collect(requests, sources, concurrency)
    records = deduplicate(raw)
    export_records(records, output, format)
    return records, errors
