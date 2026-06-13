from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from configobj import ConfigObj


class SourceHealthStore:
    """Persistent endpoint health, stored in a user-editable ConfigObj INI file."""

    def __init__(self, path: Path, failure_threshold: int = 10) -> None:
        self.path = path
        self.failure_threshold = failure_threshold
        self.config = ConfigObj(str(path), encoding="utf-8") if path.exists() else ConfigObj(encoding="utf-8")

    def is_deprecated(self, source_id: str) -> bool:
        return self.config.get(source_id, {}).get("deprecated", "false").lower() == "true"

    def record(self, source_id: str, status_code: int | None, success: bool) -> bool:
        section = self.config.setdefault(source_id, {})
        failures = 0 if success else int(section.get("consecutive_non_200", 0)) + 1
        section.update({
            "consecutive_non_200": str(failures),
            "deprecated": str(failures >= self.failure_threshold).lower(),
            "last_status": str(status_code or ""),
            "last_checked": datetime.now(timezone.utc).isoformat(),
        })
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config.filename = str(self.path)
        self.config.write()
        return failures >= self.failure_threshold
