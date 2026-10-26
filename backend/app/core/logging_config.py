import logging
import logging.config
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Called once at app startup (see app/main.py). Routes everything
    through a single, consistent format so logs are greppable in
    production regardless of whether they came from our own code,
    SQLAlchemy, or uvicorn's access log."""
    log_level = "DEBUG" if settings.DEBUG else "INFO"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": sys.stdout,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
            "loggers": {
                # Quiet by default — flip to INFO/DEBUG locally when
                # diagnosing a specific query, not on every request.
                "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
                "uvicorn.access": {"level": "INFO", "propagate": True},
                "app": {"level": log_level, "propagate": True},
            },
        }
    )
