from app.core.config import PROJECT_ROOT, get_settings


def test_content_index_path_example_is_relative(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_INDEX_PATH", "config/content")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.content_index_path == PROJECT_ROOT / "config" / "content"


def test_search_index_path_resolves_relative_to_project_root(monkeypatch) -> None:
    monkeypatch.setenv("SEARCH_INDEX_PATH", "config/files.txt")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.search_index_path == PROJECT_ROOT / "config" / "files.txt"


def test_rag_max_context_chars_default(monkeypatch) -> None:
    monkeypatch.delenv("RAG_MAX_CONTEXT_CHARS", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.rag_max_context_chars == 12000
