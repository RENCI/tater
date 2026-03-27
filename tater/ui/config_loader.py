"""Load a user-provided Python config file for the Tater CLI runner."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_config_module(path: str) -> dict[str, Any]:
    """Import a .py config file and extract well-known names.

    The module must define:

    ``Schema``
        A Pydantic BaseModel subclass used as the annotation schema.

    The module may also define:

    ``widgets``
        A list of TaterWidget instances (optional).  If the list covers all
        top-level model fields it is used as-is; if it covers only some fields
        the runner treats it as overrides and auto-generates the rest.  If
        omitted entirely, all widgets are auto-generated.

    ``title``
        App window title string (optional, defaults to
        ``"tater - document annotation"``).

    ``description``
        Optional subtitle shown below the title (optional).

    ``instructions``
        Optional markdown help text shown in the app instructions drawer.

    ``register_callbacks``
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

    schema_model = getattr(module, "Schema", None)

    return {
        "schema_model": schema_model,
        "widgets": getattr(module, "widgets", None),
        "title": getattr(module, "title", None),
        "description": getattr(module, "description", None),
        "instructions": getattr(module, "instructions", None),
        "register_callbacks": getattr(module, "register_callbacks", None),
    }
