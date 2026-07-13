import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from app.core.config import get_settings
from app.models.outlook_message import OutlookMessage
from app.services.exchange_service import ExchangeService, ExchangeServiceError

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("inbox")
    def inbox_command() -> None:
        """Read the latest Exchange inbox messages."""
        settings = get_settings()
        if not settings.exchange_username or not settings.exchange_password:
            logger.error(
                "EXCHANGE_USERNAME and EXCHANGE_PASSWORD must be configured."
            )
            raise typer.Exit(code=1)

        service = ExchangeService(
            server=settings.exchange_server,
            username=settings.exchange_username,
            email=settings.exchange_email or "",
            password=settings.exchange_password,
            autodiscover_cache_path=settings.exchange_autodiscover_cache_path,
        )

        try:
            messages = service.list_inbox(limit=50)
        except ExchangeServiceError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc

        if not messages:
            console.print("[yellow]Inbox is empty.[/yellow]")
            return

        _render_inbox_table(messages)


def _render_inbox_table(messages: list[OutlookMessage]) -> None:
    table = Table(
        title="Outlook Inbox",
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("Unread", justify="center", style="cyan", no_wrap=True)
    table.add_column("Received", style="blue", no_wrap=True)
    table.add_column("From", style="green", overflow="fold")
    table.add_column("Subject", style="white", overflow="fold")

    for message in messages:
        unread_label = "•" if not message.is_read else ""
        received_label = message.received_at.strftime("%Y-%m-%d %H:%M")
        table.add_row(
            unread_label,
            received_label,
            message.sender,
            message.subject,
        )

    console.print(table)
    console.print(f"\n[dim]{len(messages)} message(s)[/dim]")
