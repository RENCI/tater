"""Upload page layout and callbacks for hosted mode.

Flow:
  1. User visits / → sees two dcc.Upload zones (schema JSON + documents JSON)
  2. Validation feedback shown inline
  3. On valid submit → schema+docs written to a temp dir, paths stored in
     flask.session, browser redirected to /annotate
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import tempfile
from pathlib import Path

from dash import Dash, Input, Output, State, dcc, html, no_update
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
                                        leftSection=DashIconify(icon="tabler:arrow-right", width=16),
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
                        # Hidden stores for validated file contents
                        dcc.Store(id="schema-store", data=None),
                        dcc.Store(id="documents-store", data=None),
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
            ),
        ],
        gap="xs",
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def register_upload_callbacks(app: Dash) -> None:
    """Register all upload-page callbacks on the given Dash app."""

    # Validate schema upload
    @app.callback(
        Output("schema-store", "data"),
        Output("schema-feedback", "children"),
        Input("upload-schema", "contents"),
        State("upload-schema", "filename"),
        prevent_initial_call=True,
    )
    def validate_schema(contents, filename):
        if not contents:
            return None, None
        result, error = _decode_json_upload(contents, filename)
        if error:
            return None, _error_text(error)
        # Validate it's a tater schema (must have a "fields" key or similar)
        ok, msg = _validate_schema_json(result)
        if not ok:
            return None, _error_text(msg)
        field_names = [f.get("name", "?") for f in result.get("fields", [])]
        summary = f"✓ {len(field_names)} field(s): {', '.join(field_names[:8])}" + (
            f" …and {len(field_names) - 8} more" if len(field_names) > 8 else ""
        )
        return result, _success_text(summary)

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
        missing = [i for i, d in enumerate(result) if not isinstance(d, dict) or "id" not in d]
        if missing:
            return None, _error_text(
                f"Document(s) at index {missing[:3]} are missing required 'id' field."
            )
        return result, _success_text(f"✓ {len(result)} document(s) loaded.")

    # Enable start button when both stores are valid
    @app.callback(
        Output("btn-start", "disabled"),
        Input("schema-store", "data"),
        Input("documents-store", "data"),
    )
    def toggle_start(schema_data, documents_data):
        return not (schema_data and documents_data)

    # Handle submit: write temp files, store paths in flask.session, redirect
    @app.callback(
        Output("upload-location", "href"),
        Output("submit-feedback", "children"),
        Input("btn-start", "n_clicks"),
        State("schema-store", "data"),
        State("documents-store", "data"),
        prevent_initial_call=True,
    )
    def handle_submit(n_clicks, schema_data, documents_data):
        if not n_clicks:
            return no_update, no_update
        if not schema_data or not documents_data:
            return no_update, _error_text("Please upload both files before starting.")

        try:
            import flask
            tmp_dir = tempfile.mkdtemp(prefix="tater_session_")
            schema_path = os.path.join(tmp_dir, "schema.json")
            docs_path = os.path.join(tmp_dir, "documents.json")
            Path(schema_path).write_text(json.dumps(schema_data))
            Path(docs_path).write_text(json.dumps(documents_data))

            session_id = secrets.token_hex(16)
            flask.session["tater_session"] = {
                "session_id": session_id,
                "schema_path": schema_path,
                "docs_path": docs_path,
            }
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
    if "fields" not in data:
        return False, "Schema must have a 'fields' key."
    fields = data["fields"]
    if not isinstance(fields, list) or not fields:
        return False, "Schema 'fields' must be a non-empty array."
    for i, f in enumerate(fields):
        if not isinstance(f, dict) or "name" not in f or "type" not in f:
            return False, f"Field at index {i} is missing 'name' or 'type'."
    return True, ""


def _error_text(msg: str):
    return dmc.Text(msg, size="xs", c="red", mt="xs")


def _success_text(msg: str):
    return dmc.Text(msg, size="xs", c="teal", mt="xs")
