import html
import re
import unicodedata


def normalize_phrase(phrase: str) -> tuple[str, str]:
    display = re.sub(r"\s+", " ", html.unescape(unicodedata.normalize("NFKC", phrase))).strip()
    normalized = display.casefold().replace("’", "'").replace("–", "-").replace("—", "-")
    return display, normalized
