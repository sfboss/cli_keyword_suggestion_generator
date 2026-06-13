import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live

from .collectors.request_builder import default_template_context, plan_request, sanitized_request
from .config import load_source_config
from .pipeline import generate as run_generate
from .runtime.source_health import SourceHealthStore
from .ui.dashboard import RunDashboard, completion_summary

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
    color: Annotated[bool | None, typer.Option("--color/--no-color")] = None,
) -> None:
    config = load_source_config(source_config)
    if dry_run:
        requests = [
            plan_request(source, seed, default_template_context(seed))
            for seed in seeds
            for source in config.sources
            if source.enabled
        ]
        typer.echo(json.dumps({"request_count": len(requests), "requests": [sanitized_request(request) for request in requests]}, indent=2))
        return
    console = Console(stderr=True, no_color=None if color is None else not color)
    health = SourceHealthStore(health_file)
    active_source_count = sum(
        source.enabled and not source.deprecated and not health.is_deprecated(source.id)
        for source in config.sources
    )
    planned_requests = len(seeds) * active_source_count
    max_rows = max(3, min(10, console.height - 12))
    dashboard = RunDashboard(planned_requests, max_rows=max_rows)
    log_handler = _configure_file_logging(log_file)
    logger = logging.getLogger("keyword_generator")
    logger.info(
        "run_start seeds=%s planned_requests=%s source_config=%s output=%s",
        len(seeds),
        planned_requests,
        source_config,
        output,
    )

    try:
        if console.is_terminal:
            with Live(
                dashboard.render(),
                console=console,
                auto_refresh=False,
                screen=True,
                transient=True,
                vertical_overflow="crop",
                redirect_stdout=False,
                redirect_stderr=False,
            ) as live:

                def event(source: str, status: str, code: int | None, count: int) -> None:
                    dashboard.update(source, status, code, count)
                    live.update(dashboard.render(), refresh=True)

                records, errors = asyncio.run(
                    run_generate(
                        seeds,
                        source_config,
                        output,
                        format,
                        concurrency,
                        health_file,
                        event,
                    )
                )
        else:

            def event(source: str, status: str, code: int | None, count: int) -> None:
                dashboard.update(source, status, code, count)

            records, errors = asyncio.run(
                run_generate(
                    seeds,
                    source_config,
                    output,
                    format,
                    concurrency,
                    health_file,
                    event,
                )
            )
        logger.info(
            "run_complete keywords=%s failures=%s output=%s",
            len(records),
            len(errors),
            output,
        )
    finally:
        logger.removeHandler(log_handler)
        log_handler.close()

    if console.is_terminal:
        console.print(completion_summary(len(records), len(errors), output, log_file))
    else:
        console.print(
            f"exported {len(records)} unique keyword(s) to {output}; "
            f"{len(errors)} source request(s) failed; details: {log_file}",
            soft_wrap=True,
        )


def _configure_file_logging(log_file: Path) -> logging.FileHandler:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("keyword_generator")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return handler
