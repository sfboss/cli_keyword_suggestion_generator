import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

from .collectors.request_builder import plan_request, sanitized_request
from .config import load_source_config
from .pipeline import generate as run_generate

app = typer.Typer(help="Deterministic, provenance-preserving keyword research.", no_args_is_help=True)
config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")


@config_app.command("validate")
def validate(path: Path) -> None:
    config = load_source_config(path)
    typer.echo(f"valid: {len(config.sources)} source(s)")


@app.command()
def generate(
    seeds: Annotated[list[str], typer.Argument(help="Seed keywords")],
    source_config: Annotated[Path, typer.Option("--source-config", exists=True, readable=True)],
    output: Annotated[Path, typer.Option("--output")],
    format: Annotated[str, typer.Option("--format")] = "jsonl",
    concurrency: Annotated[int, typer.Option("--concurrency", min=1)] = 10,
    health_file: Annotated[Path, typer.Option("--health-file")] = Path(".keyword-generator/source-health.ini"),
    log_file: Annotated[Path, typer.Option("--log-file")] = Path(".keyword-generator/keywords.log"),
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    config = load_source_config(source_config)
    if dry_run:
        requests = [plan_request(source, seed) for seed in seeds for source in config.sources if source.enabled]
        typer.echo(json.dumps({"request_count": len(requests), "requests": [sanitized_request(request) for request in requests]}, indent=2))
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    statuses: dict[str, tuple[str, int | None, int]] = {}
    console = Console(stderr=True)

    def table() -> Table:
        result = Table("Source", "Status", "HTTP", "Results", title="Suggestion endpoint status")
        for source, (status, code, count) in sorted(statuses.items()):
            result.add_row(source, status, str(code or "-"), str(count))
        return result

    with Live(table(), console=console, refresh_per_second=8, transient=True) as live:
        def event(source: str, status: str, code: int | None, count: int) -> None:
            statuses[source] = (status, code, count)
            live.update(table())

        records, errors = asyncio.run(run_generate(seeds, source_config, output, format, concurrency, health_file, event))
    for error in errors:
        typer.echo(error, err=True)
    typer.echo(f"exported {len(records)} unique keyword(s) to {output}", err=True)
