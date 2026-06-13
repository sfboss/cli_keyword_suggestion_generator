import csv
import json
from pathlib import Path

from ..models import KeywordRecord


def export_records(records: list[KeywordRecord], path: Path, format: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    if format == "jsonl":
        path.write_text("".join(json.dumps(record.model_dump(mode="json"), sort_keys=True) + "\n" for record in records), encoding="utf-8")
    elif format == "json":
        path.write_text(json.dumps([record.model_dump(mode="json") for record in records], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif format == "csv":
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["keyword_id", "phrase", "normalized_phrase", "occurrences", "seed_terms", "source_ids", "request_ids"])
            writer.writeheader()
            for record in records:
                writer.writerow({"keyword_id": record.keyword_id, "phrase": record.phrase, "normalized_phrase": record.normalized_phrase, "occurrences": record.occurrences, "seed_terms": "|".join(sorted(record.seed_terms)), "source_ids": "|".join(sorted(record.source_ids)), "request_ids": "|".join(sorted(record.request_ids))})
    else:
        raise ValueError(f"unsupported format: {format}")
