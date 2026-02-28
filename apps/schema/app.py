"""Schema-driven Tater annotation application.

Loads a tater JSON schema file and runs an annotation app without any
Python model or widget definitions.

Run with:
    python apps/app.py --documents data/documents.json --schema data/simple_schema.json
    python apps/app.py --documents data/documents.json --schema data/simple_schema_ui.json
"""
from tater import TaterApp, parse_args, load_schema


def main() -> None:
    args = parse_args()

    schema_model = None
    widgets = None
    if args.schema:
        schema_model, widgets = load_schema(args.schema)

    app = TaterApp(
        title="tater - schema",
        theme="light",
        schema_model=schema_model,
        annotations_path=args.annotations,
    )

    if not app.load_documents(args.documents):
        return

    if widgets is not None:
        app.set_annotation_widgets(widgets)

    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
