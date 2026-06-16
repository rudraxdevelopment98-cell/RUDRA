"""Tiny logging helper so every module logs the same way."""
from __future__ import annotations

import logging
import os

_LEVEL = os.environ.get("RUDRA_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=_LEVEL,
    format="%(asctime)s  %(levelname)-7s  %(name)-18s  %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
