"""Load a user-provided Python config file for the Tater CLI runner."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_config_module(path: str) -> dict[str, Any]:
    """Import a .py config file and extract well-known names.

    The module may define any of:

    ``schema_model``
        A Pydantic BaseModel subclass (required).  If not assigned explicitly,
        the first BaseModel subclass defined in the module is used.

    ``widgets``
        A list of TaterWidget instances (required).

    ``title``
        App window title string (optional, defaults to "Tater").

    ``theme``
        ``"light"`` or ``"dark"`` (optional, defaults to ``"light"``).

    ``on_save``
        An ``OnSaveHook`` callable (optional).

    ``configure``
        A callable ``(app: TaterApp) -> None`` called after
        ``set_annotation_widgets()``.  Use for escape-hatch Dash callbacks
        that need the live app instance (optional).
    """
    module_path = Path(path).resolve()

    # Make the module's directory importable so relative imports work.
    module_dir = str(module_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    spec = importlib.util.spec_from_file_location("tater_config", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load config file: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    # Resolve schema_model: explicit assignment first, then autodiscover.
    schema_model = getattr(module, "schema_model", None)
    if schema_model is None:
        from pydantic import BaseModel

        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == module.__name__
            ):
                schema_model = obj
                break

    return {
        "schema_model": schema_model,
        "widgets": getattr(module, "widgets", None),
        "title": getattr(module, "title", "Tater"),
        "theme": getattr(module, "theme", "light"),
        "on_save": getattr(module, "on_save", None),
        "configure": getattr(module, "configure", None),
    }
