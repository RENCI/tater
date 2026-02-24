"""Complete annotation specification (schema + UI config)."""
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from .schema import AnnotationSchema, DataField
from .ui_config import UIConfig, WidgetConfig


class AnnotationSpec(BaseModel):
    """Complete annotation specification combining schema and UI configuration."""
    
    spec_version: str = Field(default="1.0", description="Specification version")
    schema: list[DataField] = Field(..., description="Data schema fields")
    ui: list[WidgetConfig] = Field(default_factory=list, description="UI widget configurations")
    
    @classmethod
    def from_file(cls, file_path: str | Path) -> "AnnotationSpec":
        """Load annotation spec from a JSON file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Spec file not found: {file_path}")
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        return cls.model_validate(data)
    
    def get_annotation_schema(self) -> AnnotationSchema:
        """Extract the annotation schema portion."""
        return AnnotationSchema(
            schema_version=self.spec_version,
            schema=self.schema
        )
    
    def get_ui_config(self) -> UIConfig:
        """Extract the UI configuration portion."""
        return UIConfig(ui=self.ui)
    
    def get_field(self, field_id: str) -> Optional[DataField]:
        """Get a schema field by ID."""
        for field in self.schema:
            if field.id == field_id:
                return field
        return None
    
    def get_widget_config(self, field_id: str) -> Optional[WidgetConfig]:
        """Get widget configuration for a field, or generate default."""
        # First check if explicit UI config exists
        for widget in self.ui:
            if widget.field == field_id:
                return widget
        
        # Generate default widget config based on field type
        field = self.get_field(field_id)
        if field is None:
            return None
        
        return self._generate_default_widget(field)
    
    def _generate_default_widget(self, field: DataField) -> WidgetConfig:
        """Generate default widget configuration for a field."""
        widget_type_map = {
            "single_choice": "radio_group",
            "multi_choice": "checkbox_group",
            "boolean": "checkbox",
            "free_text": "textarea",
            "span_annotation": "span_annotator"
        }
        
        return WidgetConfig(
            field=field.id,
            widget=widget_type_map.get(field.type, "textarea"),
            label=field.id.replace("_", " ").title(),
            description=field.description,
            orientation="vertical"
        )
