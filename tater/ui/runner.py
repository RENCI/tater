"""Entry point for the ``tater`` CLI command."""
import os

from tater.ui.cli import parse_args
from tater.ui.tater_app import TaterApp


def main() -> None:
    args = parse_args()
    if args.hosted:
        run_hosted(args)
    else:
        run_single(args)


def run_single(args) -> None:
    """Run tater in single-user mode (existing behavior, unchanged)."""
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
        widgets = widgets_from_model(schema_model)
    elif not _covers_all_fields(widgets, schema_model):
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


def run_hosted(args) -> None:
    """Run tater in hosted mode: upload page at /, annotation UI at /annotate."""
    import flask
    from dash import Dash
    from tater.ui.upload_layout import build_upload_layout, register_upload_callbacks
    from tater.ui.layout import build_layout as build_annotation_layout

    app = Dash(
        __name__,
        title="tater",
        suppress_callback_exceptions=True,
        use_pages=False,
    )
    app.server.secret_key = os.environ.get("TATER_SECRET_KEY") or _random_secret_key()

    # Cache: session_id → TaterApp. Callbacks are registered once per session_id.
    _session_cache: dict[str, object] = {}

    # Let callbacks look up the current user's TaterApp at runtime via flask.session.
    # Stored on the shared Dash app so TaterApp.__init__ can pick it up.
    def _get_hosted_app_fn():
        import flask
        session_info = flask.session.get("tater_session") or {}
        session_id = session_info.get("session_id", "")
        return _session_cache.get(session_id)

    app._tater_get_current_app = _get_hosted_app_fn

    def _on_session_ready(session_info: dict) -> None:
        """Pre-build the TaterApp when the user submits the upload form.

        Registering annotation callbacks here (during the upload submit
        response) ensures they are present in ``/_dash-dependencies`` when
        the browser lands on /annotate — avoiding a race with the layout
        endpoint that would otherwise be the first opportunity to register
        them.
        """
        session_id = session_info.get("session_id", "")
        if session_id and session_id not in _session_cache:
            tater_app = _build_session_app(app, session_info)
            if tater_app is not None:
                _session_cache[session_id] = tater_app

    # Register upload-page callbacks, passing the pre-build hook.
    register_upload_callbacks(app, on_session_ready=_on_session_ready)

    def serve_layout():
        """Return the appropriate layout based on the current Flask session."""
        session_info = flask.session.get("tater_session")
        if not session_info:
            return build_upload_layout()
        session_id = session_info.get("session_id", "")
        # Retrieve the pre-built TaterApp (built in _on_session_ready).
        tater_app = _session_cache.get(session_id)
        if tater_app is None:
            # Fallback for cases where the cache was lost (e.g. server restart).
            tater_app = _build_session_app(app, session_info)
            if tater_app is None:
                flask.session.pop("tater_session", None)
                return build_upload_layout()
            _session_cache[session_id] = tater_app
        return build_annotation_layout(tater_app)

    app.layout = serve_layout
    app.run(debug=args.debug, port=args.port, host=args.host)


def _build_session_app(dash_app, session_info: dict):
    """Construct and configure a TaterApp from session-stored temp file paths.

    Registers all callbacks on ``dash_app`` (the hosted Dash app).
    Returns None if the session data is invalid or files are missing.
    """
    from pathlib import Path
    from tater.ui.tater_app import TaterApp
    from tater.loaders import load_schema, widgets_from_model

    schema_path = session_info.get("schema_path")
    docs_path = session_info.get("docs_path")
    if not schema_path or not docs_path:
        return None
    if not Path(schema_path).exists() or not Path(docs_path).exists():
        return None

    try:
        config = load_schema(schema_path)
    except Exception:
        return None

    schema_model = config.get("schema_model")
    if schema_model is None:
        return None

    widgets = config.get("widgets") or []
    if not widgets or not _covers_all_fields(widgets, schema_model):
        widgets = widgets_from_model(schema_model, overrides=widgets)

    tater_app = TaterApp(
        title=config.get("title", "tater"),
        description=config.get("description"),
        instructions=config.get("instructions"),
        theme=config.get("theme", "light"),
        annotations_path=None,  # no auto-save in hosted mode
        schema_model=schema_model,
        is_hosted=True,
        dash_app=dash_app,
    )
    if not tater_app.load_documents(docs_path):
        return None

    tater_app.set_annotation_widgets(widgets)
    return tater_app


def _random_secret_key() -> str:
    import secrets
    return secrets.token_hex(32)


def _covers_all_fields(widgets: list, schema_model) -> bool:
    """Return True if widgets account for every top-level model field."""
    covered = {w.schema_field for w in widgets}
    return covered >= set(schema_model.model_fields.keys())
