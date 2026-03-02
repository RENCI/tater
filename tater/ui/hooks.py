"""Named extension hooks for TaterApp.

Hooks are Python callables that TaterApp invokes at specific points in the
annotation lifecycle.  They run *inside* Tater's existing Dash callback graph,
so they are side-effect sinks: they can log, write to external systems, or
mutate in-memory state, but they cannot return Dash component updates.

For UI-level customisation that needs Dash component outputs, use the escape
hatch: register callbacks directly on ``tater_app.server`` after calling
``set_annotation_widgets``.

Currently defined hooks
-----------------------

on_save
    Called after annotations are written to disk for a specific document.
    Signature: ``(doc_id: str, annotation: BaseModel) -> None``

    Example — append an audit log entry on every save::

        import json

        def log_save(doc_id: str, annotation: MyModel) -> None:
            with open("audit.jsonl", "a") as f:
                f.write(json.dumps({"doc": doc_id, **annotation.model_dump()}) + "\\n")

        app = TaterApp(..., on_save=log_save)

Adding new hooks
----------------
Add a new type alias below, add the corresponding parameter to
``TaterApp.__init__``, and call it from the appropriate place in
``callbacks.py`` or ``tater_app.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Hook type aliases — add new ones here as TaterApp gains extension points
# ---------------------------------------------------------------------------

#: Called after annotations are written to disk for a specific document.
#: ``(doc_id: str, annotation: BaseModel) -> None``
OnSaveHook = Callable[["str", "BaseModel"], None]
