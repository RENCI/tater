# Clinical Note Annotation Application

## Overview

This application is a tool for manual annotation of clinical notes. It enables annotators to systematically review clinical documents, apply structured annotations according to a predefined schema, and track their progress across a corpus of documents.

## Data Formats

### Document List Format

The application should accept either CSV or JSON format to specify which documents to annotate.

**CSV Format:**
```csv
file_path,metadata
/data/notes/patient_001.txt,{"date": "2024-01-15"}
/data/notes/patient_002.txt,{"date": "2024-01-16"}
```

Required columns:
- `file_path`: Absolute or relative path to the text file

Optional columns:
- `metadata`: JSON string with additional document information

**JSON Format:**
```json
{
  "documents": [
    {
      "file_path": "/data/notes/patient_001.txt",
      "metadata": {
        "date": "2024-01-15",
        "patient_id": "P001"
      }
    },
    {
      "file_path": "/data/notes/patient_002.txt",
      "metadata": {
        "date": "2024-01-16",
        "patient_id": "P002"
      }
    }
  ]
}
```

### Annotation Schema Format

The schema defines what types of annotations should be collected for each document.

**Schema JSON Structure:**
```json
{
  "schema_version": "1.0",
  "annotation_types": [
    {
      "id": "document_sentiment",
      "label": "Overall Sentiment",
      "type": "single_choice",
      "options": ["Positive", "Negative", "Neutral"],
      "required": true,
      "description": "The overall tone of the clinical note"
    },
    {
      "id": "conditions_mentioned",
      "label": "Conditions Mentioned",
      "type": "multi_choice",
      "options": ["Diabetes", "Hypertension", "Asthma", "Other"],
      "required": false,
      "description": "Medical conditions referenced in the note"
    },
    {
      "id": "text_entities",
      "label": "Named Entities",
      "type": "span_annotation",
      "entity_types": ["Medication", "Symptom", "Diagnosis"],
      "required": false,
      "description": "Highlight and label specific text spans"
    },
    {
      "id": "notes",
      "label": "Annotator Notes",
      "type": "free_text",
      "required": false,
      "description": "Any additional observations"
    }
  ]
}
```

Supported annotation types:
- `single_choice`: Radio button selection
- `multi_choice`: Checkbox selection (multiple allowed)
- `span_annotation`: Text highlighting with entity type labeling
- `free_text`: Open text field

### Annotation Output Format

All annotations are saved in a single JSON file per collection.

**Annotation JSON Structure:**
```json
{
  "schema_version": "1.0",
  "collection_metadata": {
    "created": "2024-01-20T09:00:00Z",
    "last_modified": "2024-01-20T10:30:00Z"
  },
  "annotations": [
    {
      "file_path": "/data/notes/patient_001.txt",
      "annotator": "user@example.com",
      "timestamp": "2024-01-20T10:30:00Z",
      "flagged_for_review": false,
      "annotations": {
        "document_sentiment": "Positive",
        "conditions_mentioned": ["Diabetes", "Hypertension"],
        "text_entities": [
          {
            "text": "metformin",
            "start": 145,
            "end": 154,
            "entity_type": "Medication"
          },
          {
            "text": "elevated blood sugar",
            "start": 78,
            "end": 98,
            "entity_type": "Symptom"
          }
        ],
        "notes": "Patient shows good compliance with treatment plan"
      },
      "status": "completed"
    },
    {
      "file_path": "/data/notes/patient_002.txt",
      "annotator": "user@example.com",
      "timestamp": "2024-01-20T10:15:00Z",
      "flagged_for_review": true,
      "annotations": {
        "document_sentiment": "Neutral",
        "conditions_mentioned": ["Asthma"],
        "text_entities": [],
        "notes": "Unclear terminology - needs review"
      },
      "status": "completed"
    }
  ]
}
```

Status values:
- `not_started`: No annotations yet
- `in_progress`: Partially annotated
- `completed`: All required fields filled
- `flagged`: Marked for review

## User Interface Requirements

### Layout

The application should use a two-column layout:

**Left Panel (60% width):**
- Document text display area
- Read-only text view with scrolling
- Line numbers displayed
- Highlighted text spans for entity annotations
- Document metadata display at top (filename, any metadata fields)

**Right Panel (40% width):**
- Annotation controls organized by annotation type
- Progress indicator showing current document number / total documents
- Navigation controls
- Review flag checkbox
- Save button (with auto-save indicator)

### Document Navigation

**Controls:**
- "Previous" button: Navigate to previous document
- "Next" button: Navigate to next document
- Document dropdown: Select any document by filename
- Keyboard shortcuts: Arrow keys or Ctrl+Left/Right for navigation

**Behavior:**
- Auto-save current annotations before navigating away
- Show warning if required fields are incomplete
- Highlight completed documents (green), in-progress (yellow), not started (gray) in dropdown

### Annotation Interactions

**Single Choice (Radio Buttons):**
- Display as radio button group
- Clear selection button available

**Multi Choice (Checkboxes):**
- Display as checkbox group
- Allow multiple selections

**Span Annotation (Text Highlighting):**
- User selects text in the document panel
- Popup appears with entity type selector
- Selected text is highlighted with color-coded background (different color per entity type)
- Click on highlighted span to view/edit/delete
- List of all annotations displayed below document with jump-to functionality

**Free Text:**
- Multi-line text area
- No character limit

### Review Flag

- Checkbox labeled "Flag for Review"
- When checked:
  - Sets `flagged_for_review: true` in annotation file
  - Document appears with special indicator in navigation
  - Optional text field for review reason

### Progress Tracking

**Display:**
- "Document X of Y" counter
- Progress bar showing completion percentage
- Statistics: Completed / In Progress / Not Started / Flagged counts

**Saving:**
- Auto-save every 30 seconds if changes detected
- Manual save button available
- Visual indicator showing save status (Saved / Saving / Unsaved changes)

## Functional Requirements

### Document Loading

1. User provides path to CSV/JSON document list file
2. User provides path to schema JSON file
3. Application validates both files
4. Application loads and displays first document
5. If annotation file exists, load all previous annotations for the collection

### Annotation Editing

- Users can modify existing annotations at any time
- Changes are reflected immediately in the UI
- Previous annotation values are overwritten in the collection file (no version history in v1)

### Validation

- Required fields must be completed before document is marked "completed"
- Warning shown when navigating away from incomplete required fields
- Schema validation on load (proper JSON structure)

### Multi-user Considerations

- Single user mode for v1 (no concurrent editing)
- Annotator identified by system username or config file
- Each annotator's work saved to separate directory (optional enhancement)

### Error Handling

- Graceful handling of missing document files (show error, skip to next)
- Invalid schema format: Show error message, prevent startup
- Failed save: Show error banner, retry option
- Corrupted annotation file: Start fresh with empty annotations, show warning and backup corrupted file

## Technical Architecture

### File Structure

```
tater/
├── src/
│   ├── app.py                 # Main Dash application
│   ├── components/
│   │   ├── document_viewer.py # Left panel document display
│   │   ├── annotation_panel.py # Right panel annotation controls
│   │   └── navigation.py      # Navigation controls
│   ├── data/
│   │   ├── loader.py          # Load documents and schema
│   │   ├── storage.py         # Save/load annotations
│   │   └── validator.py       # Schema and data validation
│   └── utils/
│       ├── config.py          # Configuration management
│       └── constants.py       # App constants
├── spec/
│   └── app.md
├── tests/
├── data/                       # Sample data (not tracked)
├── annotations/                # Output directory
├── pyproject.toml             # uv project config
└── README.md
```

### State Management

Use Dash's callback system with:
- `dcc.Store` components for:
  - Current document index
  - All documents list
  - Annotation schema
  - All annotations (full collection)
  - Current document annotations
  - Dirty state (unsaved changes)
- Input/Output/State pattern for callbacks

### Key Callbacks

1. Document navigation: Update current index, save annotations to collection file
2. Annotation changes: Update annotation state for current document, mark as dirty
3. Auto-save timer: Check dirty state, save entire collection file if needed
4. Flag toggle: Update flagged status for current document
5. Schema-driven UI: Dynamically generate annotation controls from schema

### Dependencies (uv managed)

```toml
[project]
dependencies = [
    "dash>=2.14.0",
    "dash-bootstrap-components>=1.5.0",
    "pandas>=2.0.0",
    "pydantic>=2.0.0",  # For data validation
]
```

## Non-functional Requirements

### Performance

- Support up to 1,000 documents in a single session
- Document load time < 500ms for files up to 50KB
- Annotation save time < 200ms
- UI should remain responsive during auto-save

### Browser Compatibility

- Primary: Chrome/Edge (latest 2 versions)
- Secondary: Firefox, Safari (best effort)

### Deployment

- Local deployment (run on localhost)
- Single command startup: `uv run python src/app.py`
- Default port: 8050
- Configuration via config file or environment variables

### Data Storage

- Annotations saved to `./annotations/` directory by default
- Single JSON file per collection: `annotations.json`
- File can be renamed/specified via configuration
- Atomic writes to prevent corruption
- No database required for v1

## Future Enhancements (Out of Scope for v1)

- Multi-annotator support with inter-annotator agreement metrics
- Export annotations to CSV/Excel
- Search/filter documents
- Annotation history/undo functionality
- Batch operations (flag multiple documents)
- Custom color schemes for entity highlighting
- Annotation quality metrics and reporting