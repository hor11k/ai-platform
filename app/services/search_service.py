import re
from dataclasses import dataclass
from pathlib import Path

from app.core.text import normalize_text, parse_search_terms


@dataclass(frozen=True, slots=True)
class SearchResult:
    score: float
    filename: str
    project: str
    path: str


@dataclass(frozen=True, slots=True)
class _ScoredEntry:
    score: float
    filename: str
    project: str
    path: str
    sort_project: str
    sort_filename: str


class SearchService:
    """Search and rank file paths from a line-delimited index."""

    FILENAME_WEIGHT = 10.0
    PROJECT_WEIGHT = 5.0
    PATH_WEIGHT = 2.0
    ALL_TERMS_BONUS = 10.0
    WORD_BOUNDARY_BONUS = 3.0
    PREFIX_BONUS = 5.0

    _FIELD_WEIGHTS: tuple[tuple[str, float], ...] = (
        ("filename", FILENAME_WEIGHT),
        ("project", PROJECT_WEIGHT),
        ("path", PATH_WEIGHT),
    )

    def __init__(self, index_path: Path, max_results: int = 50) -> None:
        self.index_path = index_path
        self.max_results = max_results

    def search(self, query: str) -> list[SearchResult]:
        return self._search_terms(parse_search_terms(query))

    def search_words(self, words: list[str]) -> list[SearchResult]:
        return self.search(" ".join(words))

    def _search_terms(self, terms: list[str]) -> list[SearchResult]:
        if not terms:
            return []

        entries: list[_ScoredEntry] = []
        for line in self._read_index():
            path = Path(line)
            filename = path.name
            project = self._extract_project(path)
            score = self._score_entry(
                filename=filename,
                project=project,
                path=line,
                terms=terms,
            )
            if score > 0:
                entries.append(
                    _ScoredEntry(
                        score=score,
                        filename=filename,
                        project=project,
                        path=line,
                        sort_project=normalize_text(project),
                        sort_filename=normalize_text(filename),
                    )
                )

        entries.sort(
            key=lambda entry: (-entry.score, entry.sort_project, entry.sort_filename)
        )
        return [
            SearchResult(
                score=entry.score,
                filename=entry.filename,
                project=entry.project,
                path=entry.path,
            )
            for entry in entries[: self.max_results]
        ]

    def _read_index(self) -> list[str]:
        if not self.index_path.is_file():
            msg = f"Search index not found: {self.index_path}"
            raise FileNotFoundError(msg)

        return [
            line.strip()
            for line in self.index_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _extract_project(self, path: Path) -> str:
        parts = path.parts
        try:
            wrk_index = parts.index("WRK")
        except ValueError:
            return "—"

        if wrk_index + 1 < len(parts) - 1:
            return parts[wrk_index + 1]
        return "—"

    def _score_entry(
        self,
        filename: str,
        project: str,
        path: str,
        terms: list[str],
    ) -> float:
        normalized_fields = {
            "filename": normalize_text(filename),
            "project": normalize_text(project),
            "path": normalize_text(path),
        }

        total_score = 0.0
        matched_terms = 0

        for term in terms:
            for field_name, weight in self._FIELD_WEIGHTS:
                field_score = self._match_score(
                    term, normalized_fields[field_name], weight
                )
                if field_score:
                    total_score += field_score
                    matched_terms += 1
                    break

        if matched_terms == len(terms):
            total_score += self.ALL_TERMS_BONUS

        return total_score

    def _match_score(self, term: str, text: str, weight: float) -> float:
        if term not in text:
            return 0.0

        match_score = weight
        if text.startswith(term):
            match_score += self.PREFIX_BONUS
        if re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", text):
            match_score += self.WORD_BOUNDARY_BONUS
        return match_score
