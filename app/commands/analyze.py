from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from app.core.config import get_settings
from app.exceptions import OpenAIServiceError
from app.models.document_analysis import DocumentAnalysis
from app.services.analyze_service import AnalyzeService
from app.services.document_loader import DocumentLoader
from app.services.openai_service import OpenAIService

console = Console()

_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Risks", "risks"),
    ("Key Dates", "key_dates"),
    ("Key Amounts", "key_amounts"),
    ("Parties", "parties"),
    ("Action Items", "action_items"),
)


def register(app: typer.Typer) -> None:
    @app.command("analyze")
    def analyze_command(
        file: Annotated[Path, typer.Argument(help="Path to a PDF, DOCX, or TXT file.")],
    ) -> None:
        """Analyze a document and extract structured business insights."""
        settings = get_settings()
        if not settings.openai_api_key:
            logger.error("OPENAI_API_KEY is not configured.")
            raise typer.Exit(code=1)

        service = AnalyzeService(
            document_loader=DocumentLoader(),
            openai_service=OpenAIService(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                base_url=settings.openai_base_url,
                timeout=settings.openai_timeout,
            ),
        )

        try:
            analysis = service.analyze(file)
        except FileNotFoundError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc
        except ValueError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc
        except OpenAIServiceError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc

        _render_analysis(file.name, analysis)


def _render_analysis(filename: str, analysis: DocumentAnalysis) -> None:
    console.print(
        Panel(
            analysis.executive_summary,
            title=f"Executive Summary — {filename}",
            border_style="blue",
            padding=(1, 2),
        )
    )

    for title, field_name in _SECTIONS:
        items = getattr(analysis, field_name)
        console.print(f"\n[bold magenta]{title}[/bold magenta]")
        if items:
            for item in items:
                console.print(f"  [cyan]•[/cyan] {item}")
        else:
            console.print("  [dim]None identified[/dim]")
