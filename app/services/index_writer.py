from pathlib import Path

from app.services.text_extractor import TextExtractor


class IndexWriter:
    """Persist file and text indexes."""

    def __init__(
        self,
        file_index_path: Path,
        content_index_path: Path,
        text_extractor: TextExtractor | None = None,
    ) -> None:
        self._file_index_path = file_index_path
        self._content_index_path = content_index_path
        self._text_extractor = text_extractor or TextExtractor()

    def write_file_index(self, paths: list[Path]) -> int:
        self._file_index_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [str(path.resolve()) for path in sorted(paths, key=str)]
        self._file_index_path.write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )
        return len(lines)

    def write_text_index(self, path: Path) -> bool:
        if not self._text_extractor.is_indexable(path):
            return False

        text = self._text_extractor.extract(path)
        if text is None:
            return False

        self._content_index_path.mkdir(parents=True, exist_ok=True)
        output_path = self._content_index_path / f"{path.name}.txt"
        output_path.write_text(text, encoding="utf-8")
        return True
