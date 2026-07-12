import sys

from loguru import logger

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure Loguru for CLI usage."""
    settings = get_settings()

    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.environment != "production",
    )

    if settings.log_file:
        logger.add(
            settings.log_file,
            level=settings.log_level.upper(),
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            enqueue=True,
        )
