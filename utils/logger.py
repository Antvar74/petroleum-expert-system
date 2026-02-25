"""Structured logging for PETROEXPERT."""
import logging
import sys

_initialized = False

def _init_logging():
    global _initialized
    if _initialized:
        return
    root = logging.getLogger("petroexpert")
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(handler)
    _initialized = True

def get_logger(module: str) -> logging.Logger:
    _init_logging()
    return logging.getLogger(f"petroexpert.{module}")
