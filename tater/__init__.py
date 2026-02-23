"""Tater - Text Annotation Tool for Easy Research."""

__version__ = "0.1.0"

from .ui.app import TaterApp
from .ui.cli import parse_args

__all__ = [
    "TaterApp",
    "parse_args",
]
