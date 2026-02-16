"""Application constants."""

# Status values for document annotations
STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FLAGGED = "flagged"

# Annotation types
TYPE_SINGLE_CHOICE = "single_choice"
TYPE_MULTI_CHOICE = "multi_choice"
TYPE_SPAN_ANNOTATION = "span_annotation"
TYPE_FREE_TEXT = "free_text"

# Auto-save interval (milliseconds)
AUTO_SAVE_INTERVAL = 30000  # 30 seconds

# Default paths
DEFAULT_ANNOTATIONS_DIR = "./annotations"
DEFAULT_ANNOTATIONS_FILE = "annotations.json"

# Entity colors for span annotations
ENTITY_COLORS = {
    "Medication": "#FFE5B4",  # Peach
    "Symptom": "#FFB6C1",     # Light pink
    "Diagnosis": "#B0E0E6",   # Powder blue
    "Procedure": "#DDA0DD",   # Plum
    "Test": "#F0E68C",        # Khaki
}
