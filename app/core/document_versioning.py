import re
from pathlib import Path

from app.core.text import normalize_text

DATE_PREFIX = re.compile(r"^(\d{8})\s+")
VERSION_SUFFIX = re.compile(r"_v_(\d+)$", re.IGNORECASE)
TRAILING_YEAR = re.compile(r"\s+(\d{4})$")


def extract_file_date(filename: str) -> int | None:
    stem = Path(filename).stem
    match = DATE_PREFIX.search(stem)
    if match is not None:
        return int(match.group(1))

    year_match = TRAILING_YEAR.search(stem)
    if year_match is not None:
        return int(year_match.group(1)) * 10000 + 1231

    return None


def extract_version_number(filename: str) -> int:
    stem = Path(filename).stem
    stem = DATE_PREFIX.sub("", stem)
    stem = TRAILING_YEAR.sub("", stem)
    match = VERSION_SUFFIX.search(stem)
    if match is None:
        return 0
    return int(match.group(1))


def version_group_key(filename: str) -> str:
    stem = Path(filename).stem
    stem = DATE_PREFIX.sub("", stem)
    stem = VERSION_SUFFIX.sub("", stem)
    stem = TRAILING_YEAR.sub("", stem)
    return normalize_text(stem.strip())


def is_exact_filename_match(filename: str, terms: list[str]) -> bool:
    if not terms:
        return False
    stem = normalize_text(Path(filename).stem)
    return all(term in stem for term in terms)


def newest_sort_key(filename: str) -> tuple[int, int, str]:
    return (
        extract_file_date(filename) or 0,
        extract_version_number(filename),
        normalize_text(filename),
    )
