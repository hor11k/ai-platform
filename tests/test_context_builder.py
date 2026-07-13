from pathlib import Path

import pytest

from app.services.context_builder import ContextBuilder
from app.services.search_service import SearchService

FILES_INDEX = """\
/Volumes/DISK h3r/WRK/19 Химки/Договор займа Химки 2024.docx
/Volumes/DISK h3r/WRK/19 Химки/20200828 Договор займа Химки.docx
/Volumes/DISK h3r/WRK/19 Химки/20200828 Договор займа Химки_v_2.docx
/Volumes/DISK h3r/WRK/03 Match Point/Химки/Договор займа Химки 2024.docx
/Volumes/DISK h3r/WRK/18 ВТБ СПОРТ/Справка ВТБ Спорт.docx
/Volumes/DISK h3r/WRK/18 ВТБ СПОРТ/Бюджет ВТБ Спорт.docx
/Volumes/DISK h3r/WRK/00 Общее/Миграция/ДК по договорам управления.docx
/Volumes/DISK h3r/WRK/01 МСТК/Вопросы по договору на проектирование МСТК (003).docx
"""

CONTENT_FILES = {
    "Договор займа Химки 2024.docx.txt": (
        "Договор займа для проекта Химки от 2024 года. Сумма займа 10 000 000 рублей."
    ),
    "20200828 Договор займа Химки.docx.txt": "Старая версия договора займа по Химкам.",
    "20200828 Договор займа Химки_v_2.docx.txt": "Вторая версия договора займа.",
    "Справка ВТБ Спорт.docx.txt": (
        "Справка по проекту ВТБ Спорт. Основные риски и сроки реализации."
    ),
    "Бюджет ВТБ Спорт.docx.txt": "Бюджет проекта ВТБ Спорт на 2025 год.",
    "ДК по договорам управления.docx.txt": "Договор управления по проекту Фордевинд.",
    "Вопросы по договору на проектирование МСТК (003).docx.txt": (
        "Вопросы по договору на проектирование МСТК."
    ),
}

KHIMKI_LOAN_QUESTION = "Где лежит последний договор займа по Химкам?"


@pytest.fixture
def indexes(tmp_path: Path) -> tuple[Path, Path]:
    files_index = tmp_path / "files.txt"
    files_index.write_text(FILES_INDEX, encoding="utf-8")

    content_index = tmp_path / "content"
    content_index.mkdir()
    for name, text in CONTENT_FILES.items():
        (content_index / name).write_text(text, encoding="utf-8")

    return files_index, content_index


@pytest.fixture
def builder_kwargs(indexes: tuple[Path, Path]) -> dict:
    files_index, content_index = indexes
    return {
        "search_service": SearchService(files_index),
        "content_index_path": content_index,
        "max_context_chars": 4096,
    }


def test_context_builder_combines_path_and_content_hits(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build("договор займа химки")

    assert len(result.chunks) >= 1
    assert any("Химки" in chunk.path for chunk in result.chunks)
    assert any("займа" in chunk.content for chunk in result.chunks)
    assert result.confidence > 0


def test_context_builder_prefers_newest_version(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build("договор займа химки")

    assert result.chunks[0].filename == "Договор займа Химки 2024.docx"
    grouped = next(
        group
        for group in result.source_groups
        if "договор займа химки" in group.primary.version_group
    )
    assert len(grouped.alternate_paths) >= 1


def test_context_builder_groups_duplicate_versions(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build("договор займа химки")
    loan_groups = [
        group
        for group in result.source_groups
        if "договор займа химки" in group.primary.version_group
    ]

    assert len(loan_groups) == 1
    assert loan_groups[0].alternate_paths


def test_context_builder_finds_vtb_sport_documents(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build("документы по ВТБ Спорт")
    paths = {chunk.path for chunk in result.chunks}

    assert any("ВТБ СПОРТ" in path for path in paths)
    assert len(paths) >= 2


def test_context_builder_respects_max_sources(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs, max_sources=1)

    result = builder.build("втб спорт")

    assert len(result.chunks) == 1


def test_context_builder_format_context_includes_paths(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)
    result = builder.build("втб спорт")

    formatted = ContextBuilder.format_context(result.chunks)

    assert "Path:" in formatted
    assert "Content:" in formatted
    assert "ВТБ СПОРТ" in formatted


def test_context_builder_empty_question(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build("")

    assert result.chunks == []
    assert result.confidence == 0
    assert result.retrieval_debug == []


def test_context_builder_khimki_loan_prefers_loan_contract(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build(KHIMKI_LOAN_QUESTION)

    assert result.chunks
    top = result.chunks[0]
    assert "Договор займа" in top.filename
    assert "Химки" in top.path
    assert top.reason.startswith("filename")
    assert result.retrieval_debug
    assert result.retrieval_debug[0].filename == top.filename
    assert "договорам управления" not in top.filename.lower()


def test_context_builder_khimki_loan_debug_includes_reason(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build(KHIMKI_LOAN_QUESTION)

    assert any(item.reason.startswith("filename") for item in result.retrieval_debug)
    assert all(item.filename for item in result.retrieval_debug)
    assert all(item.score > 0 for item in result.retrieval_debug)


def test_context_builder_khimki_loan_skips_content_fallback(builder_kwargs) -> None:
    builder = ContextBuilder(**builder_kwargs)

    result = builder.build(KHIMKI_LOAN_QUESTION)

    assert not any(item.reason.startswith("content") for item in result.retrieval_debug)
