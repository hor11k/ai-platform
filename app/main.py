from typing import Annotated

import typer
from rich.console import Console

from app.commands.analyze import register as register_analyze
from app.commands.ask import register as register_ask
from app.commands.find import register as register_find
from app.commands.ingest import register as register_ingest
from app.commands.inbox import register as register_inbox
from app.commands.open import register as register_open
from app.core.config import get_settings
from app.core.logger import setup_logging

app = typer.Typer(
    name="ai",
    help="AI Platform — production-ready CLI foundation.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    """AI Platform CLI entry point."""
    settings = get_settings()
    if verbose:
        settings.log_level = "DEBUG"

    setup_logging()
    console.print(
        f"[bold blue]{settings.app_name}[/bold blue] ({settings.environment})"
    )


register_find(app)
register_analyze(app)
register_ask(app)
register_ingest(app)
register_inbox(app)
register_open(app)

REGISTERED_COMMAND_NAMES = ("find", "analyze", "ask", "ingest", "inbox", "open")


if __name__ == "__main__":
    app()
