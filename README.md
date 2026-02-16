# Tater - Clinical Note Annotation Application

A web-based tool for manual annotation of clinical notes using Dash.

## Features

- Load and annotate clinical documents
- Flexible annotation schema support (single choice, multi choice, span annotations, free text)
- Progress tracking across document collections
- Auto-save functionality
- Flag documents for review
- Export annotations to JSON

## Installation

This project uses `uv` for dependency management.

```bash
# Install dependencies
uv sync
```

## Quick Start

1. **Prepare your data:**
   - Create a JSON or CSV file listing your documents (see `data/documents.json` for example)
   - Create an annotation schema JSON file (see `data/sample_schema.json` for example)
   - Place your clinical note text files in a directory

2. **Run the application:**
   ```bash
   uv run python src/app.py
   ```

3. **Open your browser:**
   - Navigate to http://localhost:8050
   - Click "Choose Document List File" and upload your document list (CSV or JSON)
   - Click "Choose Schema File" and upload your annotation schema (JSON)
   - Click "Load and Start Annotating"

## Sample Data

Sample data is provided in the `data/` directory:
- `data/documents.json` - Sample document list
- `data/sample_schema.json` - Sample annotation schema
- `data/note_001.txt`, `note_002.txt`, `note_003.txt` - Sample clinical notes

To try it out:
1. Start the app: `uv run python src/app.py`
2. Upload `data/documents.json` as the document list
3. Upload `data/sample_schema.json` as the schema
4. Click "Load and Start Annotating"

## Configuration

Configure the application using environment variables:

- `TATER_ANNOTATIONS_DIR` - Directory for saving annotations (default: `./annotations`)
- `TATER_ANNOTATIONS_FILE` - Annotation file name (default: `annotations.json`)
- `TATER_PORT` - Server port (default: `8050`)
- `TATER_DEBUG` - Debug mode (default: `False`)
- `TATER_ANNOTATOR` - Annotator name (default: system username)

Example:
```bash
TATER_ANNOTATOR="jane@example.com" uv run python src/app.py
```

## Document List Format

**JSON Format:**
```json
{
  "documents": [
    {
      "file_path": "/path/to/document.txt",
      "metadata": {
        "date": "2024-01-15",
        "patient_id": "P001"
      }
    }
  ]
}
```

**CSV Format:**
```csv
file_path,metadata
/path/to/document.txt,"{\"date\": \"2024-01-15\"}"
```

## Annotation Schema Format

```json
{
  "schema_version": "1.0",
  "annotation_types": [
    {
      "id": "sentiment",
      "label": "Document Sentiment",
      "type": "single_choice",
      "options": ["Positive", "Negative", "Neutral"],
      "required": true,
      "description": "Overall tone of the document"
    }
  ]
}
```

Supported annotation types:
- `single_choice` - Radio button selection
- `multi_choice` - Checkbox selection (multiple allowed)
- `span_annotation` - Text highlighting with entity type labeling
- `free_text` - Open text field

## Output

Annotations are saved in a single JSON file (default: `annotations/annotations.json`):

```json
{
  "schema_version": "1.0",
  "collection_metadata": {
    "created": "2024-01-20T09:00:00Z",
    "last_modified": "2024-01-20T10:30:00Z"
  },
  "annotations": [
    {
      "file_path": "/path/to/document.txt",
      "annotator": "user@example.com",
      "timestamp": "2024-01-20T10:30:00Z",
      "flagged_for_review": false,
      "annotations": {
        "sentiment": "Positive"
      },
      "status": "completed"
    }
  ]
}
```

## Project Structure

```
tater/
├── src/
│   ├── app.py                 # Main application
│   ├── components/            # UI components
│   ├── data/                  # Data loading and storage
│   └── utils/                 # Utilities and config
├── data/                      # Sample data
├── annotations/               # Output directory
├── spec/                      # Specification
└── pyproject.toml            # Project configuration
```

## License

MIT
