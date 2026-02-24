"""Command-line interface utilities for Tater."""
import argparse
import os
from argparse import Namespace


def parse_args() -> Namespace:
    """Parse command-line arguments for Tater applications.
    
    Returns:
        Namespace object with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Tater - Text Annotation Tool for Easy Research"
    )
    parser.add_argument(
        "--documents",
        required=True,
        help="Path to documents file (JSON or CSV)"
    )
    parser.add_argument(
        "--schema",
        required=False,
        help="Path to annotation schema file (JSON)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("TATER_DEBUG", "").lower() in ("true", "1", "yes"),
        help="Enable debug mode with hot reloading (or set TATER_DEBUG env var)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("TATER_PORT", "8050")),
        help="Port to run the server on (default: 8050, or TATER_PORT env var)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("TATER_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1, or TATER_HOST env var)"
    )
    
    return parser.parse_args()
