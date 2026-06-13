import hashlib

from ..models import KeywordRecord, RawKeyword
from .normalize import normalize_phrase


def deduplicate(raw: list[RawKeyword]) -> list[KeywordRecord]:
    records: dict[str, KeywordRecord] = {}
    for item in raw:
        display, normalized = normalize_phrase(item.phrase)
        keyword_id = hashlib.sha256(normalized.encode()).hexdigest()[:20]
        if keyword_id in records:
            record = records[keyword_id]
            record.occurrences += 1
            record.seed_terms.add(item.seed)
            record.source_ids.add(item.source_id)
            record.request_ids.add(item.request_id)
        else:
            records[keyword_id] = KeywordRecord(keyword_id=keyword_id, phrase=display, display_phrase=display, normalized_phrase=normalized, seed_terms={item.seed}, source_ids={item.source_id}, request_ids={item.request_id}, source_metadata={item.source_id: item.metadata})
    return sorted(records.values(), key=lambda record: record.normalized_phrase)
