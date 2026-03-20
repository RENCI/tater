"""Entry point for the ``tater`` CLI command."""
from tater.ui.cli import parse_args
from tater.ui.tater_app import TaterApp

def main() -> None:
    args = parse_args()

    if args.config:
        from tater.ui.config_loader import load_config_module
        config = load_config_module(args.config)
    else:
        from tater.loaders import load_schema
        config = load_schema(args.schema)

    schema_model = config.get("schema_model")
    widgets = config.get("widgets")
    title = config.get("title")
    description = config.get("description")
    instructions = config.get("instructions")
    theme = config.get("theme", "light")
    register_callbacks = config.get("register_callbacks")

    if schema_model is None:
        raise SystemExit("error: no schema_model found in config")

    from tater.loaders import widgets_from_model

    if not widgets:
        # No widgets supplied — auto-generate all.
        widgets = widgets_from_model(schema_model)
    elif not _covers_all_fields(widgets, schema_model):
        # Partial list — treat as overrides, auto-generate the rest.
        if any(w.schema_field == "" for w in widgets):
            import warnings
            warnings.warn(
                "Widget list contains dividers but does not cover all model fields. "
                "Dividers will be dropped. Provide widgets for all fields to preserve them.",
                UserWarning,
                stacklevel=2,
            )
        widgets = widgets_from_model(schema_model, overrides=widgets)

    app = TaterApp(
        title=title,
        description=description,
        instructions=instructions,
        theme=theme,
        annotations_path=args.annotations,
        schema_model=schema_model,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)

    if register_callbacks is not None:
        register_callbacks(app)

    app.run(debug=args.debug, port=args.port, host=args.host)


def _covers_all_fields(widgets: list, schema_model) -> bool:
    """Return True if widgets account for every top-level model field."""
    covered = {w.schema_field for w in widgets}
    return covered >= set(schema_model.model_fields.keys())
