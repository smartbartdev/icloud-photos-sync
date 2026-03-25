from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(log_file: Path, verbose: bool) -> logging.Logger:
    """Configure console + file logging."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ipb")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
