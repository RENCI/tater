"""Tater 2.0: Pydantic-First Document Annotation System."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from tater.models.span import SpanAnnotation
from tater.widgets.span import SpanBaseWidget, SpanAnnotationWidget, SpanPopupWidget, EntityType
from tater.loaders import load_schema, parse_schema, widgets_from_model
from tater.ui.tater_app import TaterApp

if TYPE_CHECKING:
    from pydantic import BaseModel


def annotate(
    model: type[BaseModel],
    documents,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    instructions: Optional[str] = None,
    annotations_path: Optional[str] = None,
    on_save=None,
    port: int = 8050,
    jupyter_mode: str = "inline",
    debug: bool = False,
) -> TaterApp:
    """Launch a Tater annotation app inside a Jupyter notebook.

    Args:
        model: Pydantic model class defining the annotation schema.
        documents: Path to documents file (JSON, CSV, TSV, or Excel), a
            ``list[dict]`` with at least a ``text`` key per item, or a
            ``pandas.DataFrame`` with a ``text`` column.
        title: Optional app title.
        description: Optional subtitle shown below the title.
        instructions: Optional markdown help text shown in the help drawer.
        annotations_path: Where to save annotations. Defaults to
            <documents_stem>_annotations.json next to the documents file.
        on_save: Optional callback invoked after each auto-save.
        port: Port for the Dash server.
        jupyter_mode: Dash Jupyter rendering mode — "inline" (iframe in cell
            output), "tab" (new browser tab), or "jupyterlab" (side panel).
        debug: Enable Dash debug mode.

    Returns:
        TaterApp instance. Call ``app.get_annotations()`` in a later cell to
        retrieve results after annotating.

    Example::

        import tater
        from pydantic import BaseModel
        from typing import Optional, Literal

        class Review(BaseModel):
            sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
            notes: Optional[str] = None

        app = tater.annotate(Review, "reviews.json")
        # Annotate in the embedded UI, then in a new cell:
        results = app.get_annotations()
    """
    app = TaterApp(
        title=title,
        description=description,
        instructions=instructions,
        annotations_path=annotations_path,
        schema_model=model,
        on_save=on_save,
    )
    if not app.load_documents(documents):
        raise RuntimeError(f"Failed to load documents from {documents!r}")
    widgets = widgets_from_model(model)
    app.set_annotation_widgets(widgets)
    app.run(port=port, jupyter_mode=jupyter_mode, debug=debug)
    return app


__all__ = [
    "TaterApp",
    "annotate",
    "SpanAnnotation",
    "SpanBaseWidget",
    "SpanAnnotationWidget",
    "SpanPopupWidget",
    "EntityType",
    "load_schema",
    "parse_schema",
    "widgets_from_model",
]
