from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from app.core.config import get_settings
from app.exceptions import OpenAIServiceError
from app.models.ask_response import AskResponse
from app.services.context_builder import ContextBuilder
from app.services.openai_service import OpenAIService
from app.services.rag_service import RagService
from app.services.search_service import SearchService

console = Console()

LOW_CONFIDENCE_THRESHOLD = 70


def register(app: typer.Typer) -> None:
    @app.command("ask")
    def ask_command(
        question: Annotated[
            str,
            typer.Argument(help="Natural-language question about indexed documents."),
        ],
    ) -> None:
        """Search indexed documents and answer in natural language."""
        settings = get_settings()
        if not settings.openai_api_key:
            logger.error("OPENAI_API_KEY is not configured.")
            raise typer.Exit(code=1)

        service = RagService(
            context_builder=ContextBuilder(
                search_service=SearchService(index_path=settings.search_index_path),
                content_index_path=settings.content_index_path,
                max_sources=settings.rag_max_sources,
                max_context_chars=settings.rag_max_context_chars,
            ),
            openai_service=OpenAIService(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                base_url=settings.openai_base_url,
                timeout=settings.openai_timeout,
            ),
        )

        try:
            response = service.ask(question)
        except FileNotFoundError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc
        except ValueError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc
        except OpenAIServiceError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc

        _render_response(question, response)


def _render_response(question: str, response: AskResponse) -> None:
    if response.confidence >= LOW_CONFIDENCE_THRESHOLD:
        confidence_style = "green"
    else:
        confidence_style = "yellow"
    console.print(
        f"[bold]Confidence:[/bold] "
        f"[{confidence_style}]{response.confidence}%[/{confidence_style}]"
    )

    if response.confidence < LOW_CONFIDENCE_THRESHOLD:
        console.print(
            "[yellow]The answer may be incomplete because document confidence is below "
            f"{LOW_CONFIDENCE_THRESHOLD}%.[/yellow]"
        )

    console.print(
        Panel(
            response.answer,
            title=f"Answer — {question}",
            border_style="green",
            padding=(1, 2),
        )
    )

    console.print("\n[bold magenta]Sources[/bold magenta]")
    if not response.source_groups:
        console.print("  [dim]No sources matched[/dim]")
        return

    for group in response.source_groups:
        console.print(f"  [cyan]•[/cyan] {group.primary_path}")
        if group.alternate_paths:
            console.print("    [dim]Older versions:[/dim]")
            for alternate in group.alternate_paths:
                console.print(f"      [dim]- {alternate}[/dim]")
