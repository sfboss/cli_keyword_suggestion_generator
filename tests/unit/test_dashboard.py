import io
import json

from rich.console import Console
from typer.testing import CliRunner

from keyword_generator.cli import app
from keyword_generator.ui.dashboard import RunDashboard


def test_dashboard_is_colored_and_bounded():
    dashboard = RunDashboard(planned_requests=12, max_rows=4)
    for index in range(12):
        dashboard.update(f"source-{index}", "success", 200, index)

    stream = io.StringIO()
    console = Console(
        file=stream,
        force_terminal=True,
        color_system="standard",
        no_color=False,
        width=100,
        height=20,
    )
    console.print(dashboard.render())
    rendered = stream.getvalue()

    assert "\x1b[36m" in rendered
    assert rendered.count("source-") == 4
    assert "8 hidden" in rendered


def test_cli_summarizes_failures_without_printing_each_error(tmp_path, monkeypatch):
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "suggest",
                        "name": "Suggest",
                        "request": {"url": "https://example.test"},
                        "parser": {"type": "generic"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "keywords.log"

    async def failed_run(*args, **kwargs):
        event = args[-1]
        event("suggest", "failed", 503, 0)
        return [], [
            "suggest/request-1: HTTPStatusError: first noisy failure",
            "suggest/request-2: HTTPStatusError: second noisy failure",
        ]

    monkeypatch.setattr("keyword_generator.cli.run_generate", failed_run)
    result = CliRunner().invoke(
        app,
        [
            "generate",
            "running shoes",
            "--source-config",
            str(config_path),
            "--output",
            str(tmp_path / "running-shoes-keywords.jsonl"),
            "--log-file",
            str(log_path),
        ],
    )

    assert result.exit_code == 0
    assert "2 source request(s) failed" in result.output
    assert "first noisy failure" not in result.output
    assert "second noisy failure" not in result.output
    assert "run_start" in log_path.read_text(encoding="utf-8")
    assert "run_complete" in log_path.read_text(encoding="utf-8")
