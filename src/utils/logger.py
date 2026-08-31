"""Structured logging utility for the Olist Lakehouse Platform."""

import logging
import os
import sys
from typing import Optional


class ColorFormatter(logging.Formatter):
    """Custom color formatter for development console logging."""

    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.format_str)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def get_logger(name: Optional[str] = None, log_level: Optional[str] = None) -> logging.Logger:
    """Get or configure a standard structured logger.

    Args:
        name: Name of the logger (defaults to module name or root).
        log_level: Optional log level string (INFO, DEBUG, WARNING, ERROR).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name or "olist_lakehouse")

    if not logger.handlers:
        level_str = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Check if terminal supports color (or fallback to clean plain format)
        if sys.stdout.isatty():
            handler.setFormatter(ColorFormatter())
        else:
            fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
            handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

        logger.addHandler(handler)
        logger.propagate = False

    return logger
