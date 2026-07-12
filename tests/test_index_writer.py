from pathlib import Path

from app.services.index_writer import IndexWriter


def test_write_file_index(tmp_path: Path) -> None:
    file_index = tmp_path / "files.txt"
    content_index = tmp_path / "content"
    writer = IndexWriter(file_index, content_index)

    paths = [tmp_path / "b.txt", tmp_path / "a.txt"]
    for path in paths:
        path.write_text("text", encoding="utf-8")

    total = writer.write_file_index(paths)

    assert total == 2
    lines = file_index.read_text(encoding="utf-8").strip().splitlines()
    assert lines == sorted(str(path.resolve()) for path in paths)


def test_write_text_index_for_txt(tmp_path: Path) -> None:
    file_index = tmp_path / "files.txt"
    content_index = tmp_path / "content"
    writer = IndexWriter(file_index, content_index)
    source = tmp_path / "notes.txt"
    source.write_text("Indexed text", encoding="utf-8")

    indexed = writer.write_text_index(source)

    assert indexed is True
    output = content_index / "notes.txt.txt"
    assert output.read_text(encoding="utf-8") == "Indexed text"


def test_write_text_index_skips_non_indexable(tmp_path: Path) -> None:
    file_index = tmp_path / "files.txt"
    content_index = tmp_path / "content"
    writer = IndexWriter(file_index, content_index)
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"binary")

    indexed = writer.write_text_index(source)

    assert indexed is False
    assert not any(content_index.iterdir()) if content_index.exists() else True
