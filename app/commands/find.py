from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from app.core.config import get_settings
from app.core.text import highlight_terms
from app.models.session_state import SessionEntry
from app.services.search_service import SearchService
from app.services.session_store import SessionStore

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("find")
    def find_command(
        words: Annotated[
            list[str],
            typer.Argument(help="Search words (multiple words, no quotes needed)."),
        ],
    ) -> None:
        """Search indexed files by name, project, or path."""
        settings = get_settings()
        service = SearchService(index_path=settings.search_index_path)
        query_label = " ".join(words)

        try:
            results = service.search_words(words)
        except FileNotFoundError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc

        if not results:
            console.print(f"[yellow]No results for[/yellow] [bold]{query_label}[/bold]")
            return

        table = Table(
            title=f"Search: {query_label}",
            show_header=True,
            header_style="bold magenta",
            row_styles=["", "dim"],
            expand=True,
        )
        table.add_column("Score", justify="right", style="cyan", no_wrap=True)
        table.add_column("Filename", style="bold green", overflow="fold")
        table.add_column("Project", style="blue", overflow="fold")
        table.add_column("Path", style="white", overflow="fold")

        for result in results:
            table.add_row(
                str(result.score).removesuffix(".0"),
                highlight_terms(result.filename, words),
                highlight_terms(result.project, words),
                highlight_terms(result.path, words),
            )

        console.print(table)
        if len(results) < service.max_results:
            limit_note = ""
        else:
            limit_note = f" (max {service.max_results})"
        console.print(f"\n[dim]{len(results)} result(s){limit_note}[/dim]")
        SessionStore.save_results(
            settings.session_state_path,
            command="find",
            results=[
                SessionEntry(path=result.path, filename=result.filename)
                for result in results
            ],
        )
