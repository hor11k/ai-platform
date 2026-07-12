from pathlib import Path

import pytest

from app.services.search_service import SearchService

SAMPLE_INDEX = """\
/Volumes/DISK h3r/WRK/01 МСТК/Справка/Report Alpha.docx
/Volumes/DISK h3r/WRK/01 МСТК/Notes/alpha-notes.txt
/Volumes/DISK h3r/WRK/06 iQ/Протечки/Photo-1.jpg
/Volumes/DISK h3r/WRK/06 iQ/Справка.docx
/Volumes/DISK h3r/WRK/root-file.pdf
/Volumes/DISK h3r/WRK/02 Березки/Beta Project/beta-final.docx
/Volumes/DISK h3r/WRK/03 Match Point/Химки/Договор Химки.docx
/Volumes/DISK h3r/WRK/04 НР/Сёров/акт.docx
"""


@pytest.fixture
def index_file(tmp_path: Path) -> Path:
    path = tmp_path / "files.txt"
    path.write_text(SAMPLE_INDEX, encoding="utf-8")
    return path


def test_search_case_insensitive(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("СПРАВКА")
    filenames = {result.filename for result in results}
    assert "Справка.docx" in filenames


def test_search_multiple_words(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("alpha report")
    assert len(results) >= 1
    assert results[0].filename == "Report Alpha.docx"
    assert results[0].score >= (
        SearchService.FILENAME_WEIGHT * 2 + SearchService.ALL_TERMS_BONUS
    )


def test_search_multiple_words_without_quotes(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search_words(["договор", "химки"])
    assert len(results) >= 1
    assert results[0].filename == "Договор Химки.docx"


def test_search_yo_ye_equivalence(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("серов")
    assert len(results) == 1
    assert results[0].filename == "акт.docx"
    assert "Сёров" in results[0].path


def test_search_ranks_filename_above_path(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("alpha")
    scores = {result.filename: result.score for result in results}
    assert scores["alpha-notes.txt"] > scores["Report Alpha.docx"]


def test_search_sort_order(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("справка")
    same_score = [result for result in results if result.score == results[0].score]
    projects = [result.project for result in same_score]
    assert projects == sorted(projects, key=str.lower)


def test_search_extracts_project(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("Photo-1")
    assert len(results) == 1
    assert results[0].project == "06 iQ"


def test_search_root_files_have_dash_project(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("root-file")
    assert len(results) == 1
    assert results[0].project == "—"


def test_search_max_results(index_file: Path) -> None:
    service = SearchService(index_file, max_results=2)
    results = service.search("a")
    assert len(results) <= 2


def test_search_no_results(index_file: Path) -> None:
    service = SearchService(index_file)
    results = service.search("nonexistent-xyz-123")
    assert results == []


def test_search_empty_query(index_file: Path) -> None:
    service = SearchService(index_file)
    assert service.search("") == []
    assert service.search("   ") == []


def test_search_missing_index(tmp_path: Path) -> None:
    service = SearchService(tmp_path / "missing.txt")
    with pytest.raises(FileNotFoundError, match="Search index not found"):
        service.search("test")
