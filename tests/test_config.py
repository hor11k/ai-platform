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


def test_ingest_paths_resolve_relative_to_project_root(monkeypatch) -> None:
    monkeypatch.setenv("INGEST_WRK_PATH", "config/wrk")
    monkeypatch.setenv("INGEST_DOWNLOADS_PATH", "config/downloads")
    monkeypatch.setenv("INGEST_STATE_PATH", "config/ingest_state.json")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.ingest_wrk_path == PROJECT_ROOT / "config" / "wrk"
    assert settings.ingest_downloads_path == PROJECT_ROOT / "config" / "downloads"
    assert settings.ingest_state_path == PROJECT_ROOT / "config" / "ingest_state.json"


def test_ingest_max_workers_default(monkeypatch) -> None:
    monkeypatch.delenv("INGEST_MAX_WORKERS", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.ingest_max_workers == 4
