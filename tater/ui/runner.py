"""Entry point for the ``tater`` CLI command."""
import sys

from tater.ui.cli import parse_args
from tater.ui.tater_app import TaterApp


def main() -> None:
    args = parse_args()

    schema_model = None
    widgets = None
    title = "Tater"
    theme = "light"
    on_save = None
    configure = None

    if args.config:
        from tater.ui.config_loader import load_config_module

        config = load_config_module(args.config)
        schema_model = config["schema_model"]
        widgets = config["widgets"]
        title = config["title"]
        theme = config["theme"]
        on_save = config["on_save"]
        configure = config["configure"]
    elif args.schema:
        from tater.loaders import load_schema

        schema_model, widgets = load_schema(args.schema)
    else:
        print("error: one of --config or --schema is required", file=sys.stderr)
        sys.exit(1)

    if schema_model is None:
        print("error: no schema_model found in config", file=sys.stderr)
        sys.exit(1)

    from tater.loaders import widgets_from_model

    if not widgets:
        # No widgets supplied — auto-generate all.
        widgets = widgets_from_model(schema_model)
    elif not _covers_all_fields(widgets, schema_model):
        # Partial list — treat as overrides, auto-generate the rest.
        widgets = widgets_from_model(schema_model, overrides=widgets)

    app = TaterApp(
        title=title,
        theme=theme,
        annotations_path=args.annotations,
        schema_model=schema_model,
        on_save=on_save,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)

    if configure is not None:
        configure(app)

    app.run(debug=args.debug, port=args.port, host=args.host)


def _covers_all_fields(widgets: list, schema_model) -> bool:
    """Return True if widgets account for every top-level model field."""
    covered = {w.schema_field for w in widgets}
    return covered >= set(schema_model.model_fields.keys())
