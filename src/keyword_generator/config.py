import json
from pathlib import Path

import yaml

from .models import SourceConfig


def load_source_config(path: Path) -> SourceConfig:
    """Load and validate a YAML or JSON source configuration."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    return SourceConfig.model_validate(data)
