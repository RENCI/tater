"""Command-line interface utilities for Tater."""
import argparse


def parse_args():
    """Parse command-line arguments for Tater app."""
    parser = argparse.ArgumentParser(description="Tater Document Annotation App")
    parser.add_argument(
        "--documents",
        type=str,
        required=True,
        help="Path to documents JSON file or directory"
    )
    parser.add_argument(
        "--annotations",
        type=str,
        default="annotations.json",
        help="Path to save/load annotations"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to run the server on"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to run the server on"
    )
    return parser.parse_args()
