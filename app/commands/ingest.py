import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from app.core.config import get_settings
from app.services.ingest_service import IngestService

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("ingest")
    def ingest_command() -> None:
        """Incrementally index new or changed files from configured directories."""
        settings = get_settings()
        service = IngestService(
            scan_paths=[settings.ingest_wrk_path, settings.ingest_downloads_path],
            file_index_path=settings.search_index_path,
            content_index_path=settings.content_index_path,
            state_path=settings.ingest_state_path,
            max_workers=settings.ingest_max_workers,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task("Scanning directories...", total=1)

            def on_start(changed_count: int) -> None:
                progress.update(
                    task_id,
                    description="Indexing changed files",
                    total=max(changed_count, 1),
                    completed=0,
                )

            def on_progress(_name: str) -> None:
                progress.advance(task_id)

            result = service.ingest(
                on_start=on_start,
                progress_callback=on_progress,
            )
            progress.update(task_id, description="Ingest complete")

        _render_summary(result)


def _render_summary(result) -> None:
    table = Table(title="Ingest Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    table.add_row("Scanned files", str(result.scanned_files))
    table.add_row("New or changed", str(result.new_or_changed_files))
    table.add_row("Text indexed", str(result.text_indexed))
    table.add_row("Skipped unchanged", str(result.skipped_unchanged))
    table.add_row("Failed", str(result.failed))
    table.add_row("File index total", str(result.file_index_total))
    table.add_row("Last scan", result.last_scan_at.isoformat())
    console.print(table)

    console.print(
        Panel(
            "Incremental ingest completed successfully.",
            border_style="green",
            padding=(0, 2),
        )
    )
