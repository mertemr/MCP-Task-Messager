import logging
import os
import sys


def setup_logging() -> logging.Logger:
    """Configure and return the module logger."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger = logging.getLogger("task_messager")
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.addHandler(handler)
    logger.propagate = False

    return logger
