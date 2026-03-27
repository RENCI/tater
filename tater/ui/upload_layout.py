"""Upload page layout and callbacks for hosted mode.

Flow:
  1. User visits / → sees two dcc.Upload zones (schema JSON + documents JSON)
  2. Validation feedback shown inline; if schema references hierarchy files,
     a compact ontology upload section appears automatically
  3. On valid submit → schema+docs+hierarchy files written to a temp dir,
     paths stored in flask.session, browser redirected to /annotate
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import tempfile
from pathlib import Path

from dash import ALL, MATCH, Dash, Input, Output, State, ctx, dcc, html, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def build_upload_layout() -> dmc.MantineProvider:
    """Return the upload page root component."""
    return dmc.MantineProvider(
        defaultColorScheme="light",
        children=[
            dcc.Location(id="upload-location", refresh=True),
            dmc.Container(
                dmc.Stack(
                    [
                        dmc.Title("tater", order=1, ta="center", mt="xl"),
                        dmc.Text(
                            "Document annotation — upload your schema and documents to get started.",
                            size="sm", c="dimmed", ta="center",
                        ),
                        dmc.Paper(
                            dmc.Stack(
                                [
                                    _upload_zone(
                                        upload_id="upload-schema",
                                        label="Schema (JSON)",
                                        hint="A tater JSON schema file describing the annotation fields.",
                                        icon="tabler:file-code",
                                    ),
                                    html.Div(id="schema-feedback"),
                                    # Ontology section — rendered dynamically when schema has file refs
                                    html.Div(id="hierarchy-upload-section"),
                                    _upload_zone(
                                        upload_id="upload-documents",
                                        label="Documents (JSON)",
                                        hint="A JSON array of document objects with at least an 'id' and 'text' field.",
                                        icon="tabler:file-text",
                                    ),
                                    html.Div(id="documents-feedback"),
                                    dmc.Button(
                                        "Start Annotating",
                                        id="btn-start",
                                        fullWidth=True,
                                        disabled=True,
                                        rightSection=DashIconify(icon="tabler:arrow-right", width=16),
                                    ),
                                    html.Div(id="submit-feedback"),
                                ],
                                gap="md",
                            ),
                            p="xl",
                            withBorder=True,
                            shadow="sm",
                            radius="md",
                        ),
                        # Stores
                        dcc.Store(id="schema-store", data=None),
                        dcc.Store(id="documents-store", data=None),
                        dcc.Store(id="pending-hierarchies", data={}),
                        dcc.Store(id="hierarchy-files-store", data={}),
                    ],
                    gap="md",
                    align="stretch",
                ),
                size="sm",
                pt="xl",
            ),
        ],
    )


def _upload_zone(upload_id: str, label: str, hint: str, icon: str) -> dmc.Stack:
    return dmc.Stack(
        [
            dmc.Text(label, fw=500, size="sm"),
            dcc.Upload(
                dmc.Paper(
                    dmc.Stack(
                        [
                            DashIconify(icon=icon, width=32, color="gray"),
                            dmc.Text("Drag and drop or click to select", size="sm", c="dimmed"),
                            dmc.Text(hint, size="xs", c="dimmed", ta="center"),
                        ],
                        align="center",
                        gap="xs",
                    ),
                    p="md",
                    withBorder=True,
                    radius="md",
                    style={"cursor": "pointer", "borderStyle": "dashed"},
                ),
                id=upload_id,
                multiple=False,
                accept=".json",
                style={"borderStyle": "solid", "borderColor": "rgba(0, 0, 0, 0)"},
                style_active={"borderStyle": "solid", "borderColor": "#6c6", "borderRadius": 10},
            ),
        ],
        gap="xs",
    )


def _compact_upload_zone(upload_id) -> dcc.Upload:
    """Smaller upload zone for ontology files."""
    return dcc.Upload(
        dmc.Paper(
            dmc.Group(
                [
                    DashIconify(icon="tabler:file-upload", width=18, color="gray"),
                    dmc.Text("Drag and drop or click to select", size="xs", c="dimmed"),
                ],
                gap="xs",
                justify="center",
            ),
            p="xs",
            withBorder=True,
            radius="md",
            style={"cursor": "pointer", "borderStyle": "dashed"},
        ),
        id=upload_id,
        multiple=False,
        accept=".yaml,.yml,.json",
        style={"borderStyle": "solid", "borderColor": "rgba(0, 0, 0, 0)"},
        style_active={"borderStyle": "solid", "borderColor": "#6c6", "borderRadius": 10},
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def register_upload_callbacks(app: Dash, on_session_ready=None) -> None:
    """Register all upload-page callbacks on the given Dash app.

    Args:
        app: The Dash application instance.
        on_session_ready: Optional callable(session_info) called after a new
            session is written to flask.session.  Use this hook to pre-build
            the per-session TaterApp so that annotation callbacks are registered
            before the browser fetches ``/_dash-dependencies``.
    """

    # Validate schema upload
    @app.callback(
        Output("schema-store", "data"),
        Output("schema-feedback", "children"),
        Output("pending-hierarchies", "data"),
        Output("hierarchy-files-store", "data", allow_duplicate=True),
        Input("upload-schema", "contents"),
        State("upload-schema", "filename"),
        prevent_initial_call=True,
    )
    def validate_schema(contents, filename):
        if not contents:
            return None, None, {}, {}
        result, error = _decode_json_upload(contents, filename)
        if error:
            return None, _error_text(error), {}, {}
        ok, msg = _validate_schema_json(result)
        if not ok:
            return None, _error_text(msg), {}, {}
        def _field_name(f):
            if f.get("id"):
                return f["id"]
            if f.get("type") == "divider" or f.get("widget", {}).get("type") == "divider":
                return "divider"
            return None
        field_names = [n for f in result.get("data_schema", []) if (n := _field_name(f))]
        summary = f"✓ {len(field_names)} field(s): {', '.join(field_names[:8])}" + (
            f" …and {len(field_names) - 8} more" if len(field_names) > 8 else ""
        )
        # Collect file-path hierarchy references: {ref_name: filename}
        pending = {
            name: Path(source).name
            for name, source in result.get("hierarchies", {}).items()
            if isinstance(source, str)
        }
        return result, _success_text(summary), pending, {}

    # Render ontology upload section — one compact zone per hierarchy file
    @app.callback(
        Output("hierarchy-upload-section", "children"),
        Input("pending-hierarchies", "data"),
    )
    def render_hierarchy_section(pending):
        if not pending:
            return None
        rows = []
        for ref_name, filename in pending.items():
            rows.append(dmc.Stack(
                [
                    dmc.Text(filename, size="xs", c="dimmed"),
                    _compact_upload_zone({"type": "hierarchy-upload", "ref": ref_name}),
                    html.Div(id={"type": "hierarchy-feedback", "ref": ref_name}),
                    dcc.Store(id={"type": "hierarchy-relay", "ref": ref_name}, data=None),
                ],
                gap="4",
            ))
        return dmc.Stack(
            [dmc.Divider(), dmc.Text("Ontology Files", fw=500, size="sm")] + rows + [dmc.Divider()],
            gap="xs",
        )

    # Handle each ontology file upload independently via MATCH.
    # Resets contents to None after each upload so re-uploading always fires.
    @app.callback(
        Output({"type": "hierarchy-relay", "ref": MATCH}, "data"),
        Output({"type": "hierarchy-feedback", "ref": MATCH}, "children"),
        Output({"type": "hierarchy-upload", "ref": MATCH}, "contents"),
        Input({"type": "hierarchy-upload", "ref": MATCH}, "contents"),
        State({"type": "hierarchy-upload", "ref": MATCH}, "filename"),
        State("pending-hierarchies", "data"),
        prevent_initial_call=True,
    )
    def handle_one_hierarchy(contents, filename, pending):
        if not contents:
            return no_update, no_update, no_update
        ref_name = ctx.triggered_id["ref"]
        expected = (pending or {}).get(ref_name, "")
        if filename != expected:
            return None, _error_text(f"Expected '{expected}', got '{filename}'."), None
        try:
            _header, encoded = contents.split(",", 1)
            content = base64.b64decode(encoded).decode("utf-8")
        except Exception:
            return None, _error_text(f"Could not decode '{filename}'."), None
        return {"filename": filename, "content": content}, _success_text(f"✓ {filename}"), None

    # Relay all per-hierarchy uploads into hierarchy-files-store
    @app.callback(
        Output("hierarchy-files-store", "data", allow_duplicate=True),
        Input({"type": "hierarchy-relay", "ref": ALL}, "data"),
        prevent_initial_call=True,
    )
    def relay_hierarchy_files(relay_data_list):
        ref_names = [t["id"]["ref"] for t in ctx.inputs_list[0]]
        return {
            ref: data
            for ref, data in zip(ref_names, relay_data_list)
            if data is not None
        }

    # Validate documents upload
    @app.callback(
        Output("documents-store", "data"),
        Output("documents-feedback", "children"),
        Input("upload-documents", "contents"),
        State("upload-documents", "filename"),
        prevent_initial_call=True,
    )
    def validate_documents(contents, filename):
        if not contents:
            return None, None
        result, error = _decode_json_upload(contents, filename)
        if error:
            return None, _error_text(error)
        if not isinstance(result, list) or not result:
            return None, _error_text("Documents must be a non-empty JSON array.")
        bad = [i for i, d in enumerate(result) if not isinstance(d, dict)]
        if bad:
            return None, _error_text(f"Document(s) at index {bad[:3]} are not objects.")
        file_path_docs = [i for i, d in enumerate(result) if isinstance(d, dict) and "file_path" in d]
        if file_path_docs:
            return None, _error_text(
                "Documents with 'file_path' are not supported in hosted mode. "
                "Include document text inline using the 'text' field."
            )
        missing_text = [i for i, d in enumerate(result) if isinstance(d, dict) and "text" not in d]
        if missing_text:
            return None, _error_text(
                f"Document(s) at index {missing_text[:3]} are missing required 'text' field."
            )
        return result, _success_text(f"✓ {len(result)} document(s) loaded.")

    # Enable start button when all required uploads are present
    @app.callback(
        Output("btn-start", "disabled"),
        Input("schema-store", "data"),
        Input("documents-store", "data"),
        Input("pending-hierarchies", "data"),
        Input("hierarchy-files-store", "data"),
    )
    def toggle_start(schema_data, documents_data, pending, hierarchy_files):
        if not schema_data or not documents_data:
            return True
        if pending and set(pending.keys()) != set((hierarchy_files or {}).keys()):
            return True
        return False

    # Handle submit: write temp files, store paths in flask.session, redirect
    @app.callback(
        Output("upload-location", "href"),
        Output("submit-feedback", "children"),
        Input("btn-start", "n_clicks"),
        State("schema-store", "data"),
        State("documents-store", "data"),
        State("hierarchy-files-store", "data"),
        prevent_initial_call=True,
    )
    def handle_submit(n_clicks, schema_data, documents_data, hierarchy_files):
        if not n_clicks:
            return no_update, no_update
        if not schema_data or not documents_data:
            return no_update, _error_text("Please upload both files before starting.")

        try:
            import flask
            tmp_dir = tempfile.mkdtemp(prefix="tater_session_")

            # Write hierarchy files and rewrite schema paths to absolute temp paths
            for ref_name, file_info in (hierarchy_files or {}).items():
                hierarchy_path = os.path.join(tmp_dir, file_info["filename"])
                Path(hierarchy_path).write_text(file_info["content"])
                schema_data["hierarchies"][ref_name] = hierarchy_path

            schema_path = os.path.join(tmp_dir, "schema.json")
            docs_path = os.path.join(tmp_dir, "documents.json")
            Path(schema_path).write_text(json.dumps(schema_data))
            Path(docs_path).write_text(json.dumps(documents_data))

            session_id = secrets.token_hex(16)
            session_info = {
                "session_id": session_id,
                "schema_path": schema_path,
                "docs_path": docs_path,
            }
            flask.session["tater_session"] = session_info
            if on_session_ready is not None:
                on_session_ready(session_info)
            return "/annotate", no_update
        except Exception as e:
            return no_update, _error_text(f"Error starting session: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_json_upload(contents: str, filename: str) -> tuple[dict | list | None, str | None]:
    """Decode a base64-encoded dcc.Upload content string and parse JSON."""
    try:
        _header, encoded = contents.split(",", 1)
        decoded = base64.b64decode(encoded).decode("utf-8")
        return json.loads(decoded), None
    except (ValueError, UnicodeDecodeError):
        return None, f"Could not decode '{filename}'. Make sure it is a UTF-8 JSON file."
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in '{filename}': {e}"


def _validate_schema_json(data: dict) -> tuple[bool, str]:
    """Basic structural check for a tater JSON schema."""
    if not isinstance(data, dict):
        return False, "Schema must be a JSON object."
    if "data_schema" not in data:
        return False, "Schema must have a 'data_schema' key."
    fields = data["data_schema"]
    if not isinstance(fields, list) or not fields:
        return False, "Schema 'data_schema' must be a non-empty array."
    for i, f in enumerate(fields):
        if not isinstance(f, dict):
            return False, f"Field at index {i} is missing 'id' or 'type'."
        is_divider = f.get("type") == "divider" or f.get("widget", {}).get("type") == "divider"
        if not is_divider and ("id" not in f or "type" not in f):
            return False, f"Field at index {i} is missing 'id' or 'type'."
    return True, ""


def _error_text(msg: str):
    return dmc.Text(msg, size="xs", c="red", mt="xs")


def _success_text(msg: str):
    return dmc.Text(msg, size="xs", c="teal", mt="xs")
