from dataclasses import dataclass
from pathlib import Path

from app.core.document_versioning import (
    extract_file_date,
    extract_version_number,
    is_exact_filename_match,
    newest_sort_key,
    version_group_key,
)
from app.core.text import normalize_text, parse_search_terms
from app.services.search_service import SearchService


@dataclass(frozen=True, slots=True)
class ContextChunk:
    path: str
    filename: str
    content: str
    score: float
    has_content: bool
    version_group: str
    file_date: int | None
    version_number: int
    exact_filename_match: bool


@dataclass(frozen=True, slots=True)
class SourceGroupResult:
    primary: ContextChunk
    alternate_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextResult:
    chunks: list[ContextChunk]
    source_groups: list[SourceGroupResult]
    confidence: int


class ContextBuilder:
    """Build ranked document context from local path and content indexes."""

    CONTENT_HIT_WEIGHT = 3.0
    METADATA_ONLY_WEIGHT = 0.5
    EXACT_FILENAME_BONUS = 15.0
    EXCERPT_MAX_CHARS = 1500
    LOW_CONFIDENCE_THRESHOLD = 70

    def __init__(
        self,
        search_service: SearchService,
        content_index_path: Path,
        max_context_chars: int,
        max_sources: int = 5,
    ) -> None:
        self._search_service = search_service
        self._content_index_path = content_index_path
        self._max_sources = max_sources
        self._max_context_chars = max_context_chars
        self._files_index: list[str] | None = None

    def build(self, question: str) -> ContextResult:
        terms = parse_search_terms(question)
        if not terms:
            return ContextResult(chunks=[], source_groups=[], confidence=0)

        chunks: dict[str, ContextChunk] = {}

        for result in self._search_service.search(question):
            content = self._load_content_text(result.filename)
            chunk_content = content or result.path
            weight = 1.0 if content else self.METADATA_ONLY_WEIGHT
            exact_match = is_exact_filename_match(result.filename, terms)
            score = result.score * weight
            if exact_match:
                score += self.EXACT_FILENAME_BONUS
            self._upsert_chunk(
                chunks,
                path=result.path,
                filename=result.filename,
                content=self._excerpt(chunk_content, terms),
                score=score,
                has_content=content is not None,
                exact_filename_match=exact_match,
            )

        for chunk in self._search_content_index(terms):
            exact_match = is_exact_filename_match(chunk.filename, terms)
            score = chunk.score + (self.EXACT_FILENAME_BONUS if exact_match else 0.0)
            self._upsert_chunk(
                chunks,
                path=chunk.path,
                filename=chunk.filename,
                content=chunk.content,
                score=score,
                has_content=chunk.has_content,
                exact_filename_match=exact_match,
            )

        grouped = self._group_versions(list(chunks.values()))
        primaries = self._select_primary_chunks(grouped)
        trimmed = self._trim_chunks(primaries[: self._max_sources])
        confidence = self._compute_confidence(trimmed, terms)

        return ContextResult(
            chunks=trimmed,
            source_groups=grouped,
            confidence=confidence,
        )

    def _upsert_chunk(
        self,
        chunks: dict[str, ContextChunk],
        *,
        path: str,
        filename: str,
        content: str,
        score: float,
        has_content: bool,
        exact_filename_match: bool,
    ) -> None:
        candidate = self._make_chunk(
            path=path,
            filename=filename,
            content=content,
            score=score,
            has_content=has_content,
            exact_filename_match=exact_filename_match,
        )
        existing = chunks.get(path)
        if existing is None or self._rank_chunk(candidate) > self._rank_chunk(existing):
            chunks[path] = candidate

    def _make_chunk(
        self,
        *,
        path: str,
        filename: str,
        content: str,
        score: float,
        has_content: bool,
        exact_filename_match: bool,
    ) -> ContextChunk:
        return ContextChunk(
            path=path,
            filename=filename,
            content=content,
            score=score,
            has_content=has_content,
            version_group=version_group_key(filename),
            file_date=extract_file_date(filename),
            version_number=extract_version_number(filename),
            exact_filename_match=exact_filename_match,
        )

    def _rank_chunk(self, chunk: ContextChunk) -> tuple[float, int, int, int]:
        return (
            chunk.score,
            1 if chunk.exact_filename_match else 0,
            chunk.file_date or 0,
            chunk.version_number,
        )

    def _group_versions(self, chunks: list[ContextChunk]) -> list[SourceGroupResult]:
        groups: dict[str, list[ContextChunk]] = {}
        for chunk in chunks:
            groups.setdefault(chunk.version_group, []).append(chunk)

        results: list[SourceGroupResult] = []
        for group_chunks in groups.values():
            ordered = sorted(
                group_chunks,
                key=lambda chunk: self._rank_chunk(chunk),
                reverse=True,
            )
            primary = ordered[0]
            alternates = tuple(chunk.path for chunk in ordered[1:])
            results.append(
                SourceGroupResult(primary=primary, alternate_paths=alternates)
            )

        results.sort(key=lambda group: self._rank_chunk(group.primary), reverse=True)
        return results

    def _select_primary_chunks(
        self,
        groups: list[SourceGroupResult],
    ) -> list[ContextChunk]:
        return [group.primary for group in groups]

    def _search_content_index(self, terms: list[str]) -> list[ContextChunk]:
        if not self._content_index_path.is_dir():
            return []

        hits: list[ContextChunk] = []
        for content_file in self._content_index_path.glob("*.txt"):
            try:
                text = content_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            normalized_text = normalize_text(text)
            matched_terms = sum(1 for term in terms if term in normalized_text)
            if matched_terms == 0:
                continue

            filename = content_file.name.removesuffix(".txt")
            path = self._resolve_source_path(filename) or filename
            score = matched_terms * self.CONTENT_HIT_WEIGHT
            hits.append(
                self._make_chunk(
                    path=path,
                    filename=Path(filename).name,
                    content=self._excerpt(text, terms),
                    score=score,
                    has_content=True,
                    exact_filename_match=is_exact_filename_match(filename, terms),
                )
            )

        return hits

    def _load_content_text(self, filename: str) -> str | None:
        content_file = self._content_index_path / f"{filename}.txt"
        if not content_file.is_file():
            return None
        try:
            return content_file.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            return None

    def _resolve_source_path(self, indexed_filename: str) -> str | None:
        matches = [
            path
            for path in self._read_files_index()
            if Path(path).name == indexed_filename
        ]
        if not matches:
            return None
        return max(matches, key=lambda path: newest_sort_key(Path(path).name))

    def _read_files_index(self) -> list[str]:
        if self._files_index is None:
            index_path = self._search_service.index_path
            if not index_path.is_file():
                msg = f"Search index not found: {index_path}"
                raise FileNotFoundError(msg)
            self._files_index = [
                line.strip()
                for line in index_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        return self._files_index

    def _compute_confidence(self, chunks: list[ContextChunk], terms: list[str]) -> int:
        if not chunks or not terms:
            return 0

        top_chunk = chunks[0]
        matched_terms = sum(
            1
            for term in terms
            if any(
                term in normalize_text(chunk.filename)
                or term in normalize_text(chunk.content)
                for chunk in chunks
            )
        )
        term_coverage = matched_terms / len(terms)
        score_factor = min(1.0, top_chunk.score / (40.0 * len(terms)))
        content_factor = sum(1 for chunk in chunks if chunk.has_content) / len(chunks)
        exact_factor = 1.0 if top_chunk.exact_filename_match else 0.6

        confidence = (
            score_factor * 40.0
            + term_coverage * 35.0
            + content_factor * 15.0
            + exact_factor * 10.0
        )
        return min(100, max(0, int(round(confidence))))

    def _excerpt(self, text: str, terms: list[str]) -> str:
        if len(text) <= self.EXCERPT_MAX_CHARS:
            return text

        normalized_text = normalize_text(text)
        for term in terms:
            index = normalized_text.find(term)
            if index != -1:
                start = max(0, index - 200)
                end = min(len(text), start + self.EXCERPT_MAX_CHARS)
                return text[start:end]

        return text[: self.EXCERPT_MAX_CHARS]

    def _trim_chunks(self, chunks: list[ContextChunk]) -> list[ContextChunk]:
        trimmed: list[ContextChunk] = []
        remaining = self._max_context_chars

        for chunk in chunks:
            if remaining <= 0:
                break

            content = chunk.content
            if len(content) > remaining:
                content = content[:remaining]

            trimmed.append(
                ContextChunk(
                    path=chunk.path,
                    filename=chunk.filename,
                    content=content,
                    score=chunk.score,
                    has_content=chunk.has_content,
                    version_group=chunk.version_group,
                    file_date=chunk.file_date,
                    version_number=chunk.version_number,
                    exact_filename_match=chunk.exact_filename_match,
                )
            )
            remaining -= len(content)

        return trimmed

    @staticmethod
    def format_context(chunks: list[ContextChunk]) -> str:
        sections: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            sections.append(
                "\n".join(
                    [
                        f"--- Document {index} ---",
                        f"Path: {chunk.path}",
                        f"Filename: {chunk.filename}",
                        "Content:",
                        chunk.content,
                    ]
                )
            )
        return "\n\n".join(sections)
