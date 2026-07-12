from app.core.text import highlight_terms, normalize_text, parse_search_terms


def test_normalize_text_case_insensitive() -> None:
    assert normalize_text("СПРАВКА") == "справка"


def test_normalize_text_yo_ye_equivalence() -> None:
    assert normalize_text("Сёров") == normalize_text("Серов")
    assert normalize_text("ёлка") == normalize_text("елка")


def test_parse_search_terms() -> None:
    assert parse_search_terms("договор химки") == ["договор", "химки"]


def test_highlight_terms_marks_matches() -> None:
    highlighted = highlight_terms("Договор Химки.docx", ["договор", "химки"])
    assert "[bold yellow]" in highlighted
    assert "Договор" in highlighted
    assert "Химки" in highlighted


def test_highlight_terms_yo_ye_match() -> None:
    highlighted = highlight_terms("Сёров", ["серов"])
    assert "[bold yellow]Сёров[/bold yellow]" in highlighted
