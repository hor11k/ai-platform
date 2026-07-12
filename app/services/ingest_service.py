from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.models.ingest_result import IngestResult
from app.services.file_scanner import FileScanner
from app.services.index_writer import IndexWriter
from app.services.ingest_state import IngestState


class IngestService:
    """Incrementally scan directories and update local indexes."""

    def __init__(
        self,
        scan_paths: list[Path],
        file_index_path: Path,
        content_index_path: Path,
        state_path: Path,
        max_workers: int = 4,
    ) -> None:
        self._scanner = FileScanner(scan_paths)
        self._writer = IndexWriter(file_index_path, content_index_path)
        self._state_path = state_path
        self._max_workers = max_workers

    def ingest(
        self,
        *,
        on_start: Callable[[int], None] | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> IngestResult:
        state = IngestState.load(self._state_path)
        scanned_files = self._scanner.scan()
        changed_files = [
            scanned_file
            for scanned_file in scanned_files
            if state.is_changed(scanned_file)
        ]
        skipped_unchanged = len(scanned_files) - len(changed_files)

        if on_start is not None:
            on_start(len(changed_files))

        text_indexed = 0
        failed = 0

        if changed_files:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = {
                    executor.submit(self._writer.write_text_index, item.path): item
                    for item in changed_files
                }
                for future in as_completed(futures):
                    scanned_file = futures[future]
                    if progress_callback is not None:
                        progress_callback(scanned_file.path.name)
                    try:
                        if future.result():
                            text_indexed += 1
                    except Exception:
                        failed += 1

        for scanned_file in scanned_files:
            state.update_file(scanned_file)

        file_index_total = self._writer.write_file_index(
            [scanned_file.path for scanned_file in scanned_files]
        )
        state.mark_scanned()
        state.save(self._state_path)

        return IngestResult(
            scanned_files=len(scanned_files),
            new_or_changed_files=len(changed_files),
            text_indexed=text_indexed,
            skipped_unchanged=skipped_unchanged,
            failed=failed,
            file_index_total=file_index_total,
            last_scan_at=state.last_scan_at,
        )
