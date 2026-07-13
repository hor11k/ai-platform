from pathlib import Path

import pytest

from app.services.context_builder import ContextBuilder
from app.services.search_service import SearchService

KHIMKI_LOAN_QUESTION = "Где лежит последний договор займа по Химкам?"

FILES_INDEX = """\
/Volumes/DISK h3r/WRK/19 Химки/Договор займа Химки 2024.docx
/Volumes/DISK h3r/WRK/19 Химки/20200828 Договор займа Химки.docx
/Volumes/DISK h3r/WRK/00 Общее/Миграция/ДК по договорам управления.docx
/Volumes/DISK h3r/WRK/01 МСТК/Вопросы по договору на проектирование МСТК (003).docx
/Volumes/DISK h3r/WRK/18 ВТБ СПОРТ/Справка ВТБ Спорт.docx
"""

CONTENT_FILES = {
    "Договор займа Химки 2024.docx.txt": (
        "Договор займа для проекта Химки от 2024 года."
    ),
    "20200828 Договор займа Химки.docx.txt": "Старая версия договора займа по Химкам.",
    "ДК по договорам управления.docx.txt": "Договор управления по проекту Фордевинд.",
    "Вопросы по договору на проектирование МСТК (003).docx.txt": (
        "Вопросы по договору на проектирование МСТК."
    ),
    "Справка ВТБ Спорт.docx.txt": "Справка по проекту ВТБ Спорт.",
}


@pytest.fixture
def builder(tmp_path: Path) -> ContextBuilder:
    files_index = tmp_path / "files.txt"
    files_index.write_text(FILES_INDEX, encoding="utf-8")

    content_index = tmp_path / "content"
    content_index.mkdir()
    for name, text in CONTENT_FILES.items():
        (content_index / name).write_text(text, encoding="utf-8")

    return ContextBuilder(
        search_service=SearchService(files_index),
        content_index_path=content_index,
        max_context_chars=4096,
    )


def test_khimki_loan_question_retrieves_loan_contract_from_19_khimki(
    builder: ContextBuilder,
) -> None:
    result = builder.build(KHIMKI_LOAN_QUESTION)

    assert result.chunks
    top = result.chunks[0]
    assert "Договор займа" in top.filename
    assert "19 Химки" in top.path


def test_khimki_loan_question_top_debug_entry_is_filename_match(
    builder: ContextBuilder,
) -> None:
    result = builder.build(KHIMKI_LOAN_QUESTION)

    assert result.retrieval_debug
    top_debug = result.retrieval_debug[0]
    assert top_debug.reason.startswith("filename")
    assert "Договор займа" in top_debug.filename
    assert top_debug.score >= 200.0


def test_khimki_loan_question_does_not_rank_unrelated_contracts_first(
    builder: ContextBuilder,
) -> None:
    result = builder.build(KHIMKI_LOAN_QUESTION)

    top = result.chunks[0]
    assert "управления" not in top.filename
    assert "МСТК" not in top.filename
    assert "ВТБ" not in top.filename
