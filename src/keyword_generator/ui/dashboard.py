from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

_STATUS_STYLES = {
    "running": "bold cyan",
    "success": "bold green",
    "failed": "bold red",
    "deprecated": "bold yellow",
}
_TERMINAL_STATUSES = {"success", "failed", "deprecated"}


@dataclass
class SourceStatus:
    status: str
    code: int | None
    count: int
    sequence: int


class RunDashboard:
    """A compact, bounded Rich dashboard for collection status events."""

    def __init__(self, planned_requests: int, max_rows: int = 10) -> None:
        self.planned_requests = planned_requests
        self.max_rows = max(3, max_rows)
        self.started_at = monotonic()
        self.completed_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.keyword_count = 0
        self._sequence = 0
        self._statuses: dict[str, SourceStatus] = {}

    @property
    def visible_statuses(self) -> list[tuple[str, SourceStatus]]:
        statuses = sorted(
            self._statuses.items(),
            key=lambda item: (item[1].status != "running", -item[1].sequence),
        )
        return statuses[: self.max_rows]

    def update(self, source: str, status: str, code: int | None, count: int) -> None:
        self._sequence += 1
        if status in _TERMINAL_STATUSES:
            self.completed_requests += 1
            self.successful_requests += status == "success"
            self.failed_requests += status in {"failed", "deprecated"}
            self.keyword_count += count
        self._statuses[source] = SourceStatus(status, code, count, self._sequence)

    def render(self) -> RenderableType:
        elapsed = monotonic() - self.started_at
        total = max(self.planned_requests, 1)

        metrics = Table.grid(expand=True)
        metrics.add_column(ratio=1)
        metrics.add_column(ratio=1)
        metrics.add_column(ratio=1)
        metrics.add_column(ratio=1)
        metrics.add_row(
            _metric("Requests", f"{self.completed_requests}/{self.planned_requests}", "cyan"),
            _metric("Succeeded", str(self.successful_requests), "green"),
            _metric("Failed", str(self.failed_requests), "red"),
            _metric("Keywords", str(self.keyword_count), "magenta"),
        )
        progress = ProgressBar(
            total=total,
            completed=min(self.completed_requests, total),
            complete_style="cyan",
            finished_style="green",
            pulse_style="cyan",
        )
        header = Panel(
            Group(metrics, progress),
            title=f"[bold cyan]Keyword collection[/] [dim]{elapsed:0.1f}s[/]",
            border_style="cyan",
            padding=(0, 1),
        )

        statuses = Table(
            box=box.SIMPLE_HEAD,
            expand=True,
            header_style="bold cyan",
            padding=(0, 1),
        )
        statuses.add_column("Source", ratio=4, overflow="ellipsis", no_wrap=True)
        statuses.add_column("Status", ratio=2, no_wrap=True)
        statuses.add_column("HTTP", justify="right", no_wrap=True)
        statuses.add_column("Results", justify="right", no_wrap=True)
        visible_statuses = self.visible_statuses
        for source, source_status in visible_statuses:
            statuses.add_row(
                source,
                Text(source_status.status, style=_STATUS_STYLES.get(source_status.status, "white")),
                _http_status(source_status.code),
                str(source_status.count),
            )
        if not self._statuses:
            statuses.add_row("[dim]Waiting for requests...[/]", "", "", "")

        hidden = max(0, len(self._statuses) - len(visible_statuses))
        footer = Text(
            f"Showing active and recent sources"
            f"{f' · {hidden} hidden' if hidden else ''} · failures are written to the log",
            style="dim",
        )
        return Group(header, statuses, footer)


def completion_summary(
    keyword_count: int,
    error_count: int,
    output: Path,
    log_file: Path,
) -> Panel:
    status_style = "green" if keyword_count or not error_count else "yellow"
    body = Text()
    body.append(f"{keyword_count} unique keyword(s)", style=f"bold {status_style}")
    body.append(f" exported to {output}\n")
    if error_count:
        body.append(f"{error_count} source request(s) failed", style="bold yellow")
        body.append(f"; details: {log_file}")
    else:
        body.append("All source requests completed without errors.", style="green")
    return Panel(body, title="[bold]Collection complete[/]", border_style=status_style, padding=(0, 1))


def _metric(label: str, value: str, style: str) -> Text:
    text = Text()
    text.append(f"{label} ", style="dim")
    text.append(value, style=f"bold {style}")
    return text


def _http_status(code: int | None) -> Text:
    if code is None:
        return Text("-", style="dim")
    return Text(str(code), style="green" if 200 <= code < 300 else "red")
