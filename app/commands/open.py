from typing import Annotated

import typer
from loguru import logger
from rich.console import Console

from app.core.config import get_settings
from app.services.open_service import OpenService, OpenServiceError

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("open")
    def open_command(
        target: Annotated[
            str,
            typer.Argument(
                help='Result number, "last", or a filename from the last results.'
            ),
        ],
    ) -> None:
        """Open a document from the last ai find or ai ask results."""
        settings = get_settings()
        service = OpenService(session_path=settings.session_state_path)

        try:
            result = service.open(target)
        except OpenServiceError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc

        console.print(f"[bold]Opening:[/bold] {result.relative_path}")
