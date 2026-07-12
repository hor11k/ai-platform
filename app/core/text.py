from rich.markup import escape


def normalize_text(text: str) -> str:
    """Normalize text for case-insensitive Russian-aware matching."""
    return text.lower().replace("ё", "е")


def parse_search_terms(query: str) -> list[str]:
    """Split a query into normalized search terms."""
    return [normalize_text(term) for term in query.split() if term.strip()]


def highlight_terms(text: str, words: list[str]) -> str:
    """Wrap matched terms in Rich markup for table highlighting."""
    terms = parse_search_terms(" ".join(words))
    if not terms:
        return escape(text)

    normalized_text = normalize_text(text)
    spans: list[tuple[int, int]] = []

    for term in terms:
        start = 0
        while True:
            index = normalized_text.find(term, start)
            if index == -1:
                break
            spans.append((index, index + len(term)))
            start = index + 1

    if not spans:
        return escape(text)

    merged = _merge_spans(spans)
    parts: list[str] = []
    cursor = 0

    for start, end in merged:
        if cursor < start:
            parts.append(escape(text[cursor:start]))
        parts.append(f"[bold yellow]{escape(text[start:end])}[/bold yellow]")
        cursor = end

    if cursor < len(text):
        parts.append(escape(text[cursor:]))

    return "".join(parts)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    sorted_spans = sorted(spans)
    merged: list[tuple[int, int]] = []

    for start, end in sorted_spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return merged
