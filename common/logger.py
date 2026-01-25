"""
Centralized logging configuration for GG Archive.

This module provides a unified logging system that writes logs to both
console and file based on settings.log_file_path.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

_logger_initialized = False


def setup_logger(log_file_path: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up the application logger with file and console handlers.

    Args:
        log_file_path: Path to the log file. If None, uses default from Settings.
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance.
    """
    global _logger_initialized

    logger = logging.getLogger("gg_archive")

    # Avoid duplicate initialization
    if _logger_initialized:
        return logger

    logger.setLevel(level)

    # Log format
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file_path is None:
        from config.settings import Settings
        settings = Settings()
        log_file_path = settings.log_file_path

    # Ensure log directory exists
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _logger_initialized = True

    return logger


def get_logger(name: str = "gg_archive") -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically the module name).

    Returns:
        Logger instance.
    """
    # Ensure the root logger is set up
    if not _logger_initialized:
        setup_logger()

    # Return a child logger for the specific module
    if name == "gg_archive":
        return logging.getLogger(name)
    return logging.getLogger(f"gg_archive.{name}")
