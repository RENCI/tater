"""Annotation schema models."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class DataField(BaseModel):
    """Definition of a single data field in the annotation schema."""
    
    id: str = Field(..., description="Unique identifier for this field")
    type: Literal["single_choice", "multi_choice", "boolean", "free_text", "span_annotation"] = Field(
        ..., description="Data type of the field"
    )
    options: Optional[list[str]] = Field(
        None, description="Available options for choice fields"
    )
    required: bool = Field(default=False, description="Whether this field is required")
    default: Optional[Any] = Field(None, description="Default value for the field")
    description: Optional[str] = Field(None, description="Human-readable description")
    
    def validate_value(self, value: Any) -> bool:
        """Validate that a value is appropriate for this field type."""
        if value is None:
            return not self.required
        
        if self.type == "single_choice":
            return value in (self.options or [])
        elif self.type == "multi_choice":
            return isinstance(value, list) and all(v in (self.options or []) for v in value)
        elif self.type == "boolean":
            return isinstance(value, bool)
        elif self.type == "free_text":
            return isinstance(value, str)
        elif self.type == "span_annotation":
            # Span annotations should be a list of dicts with start, end, label
            return isinstance(value, list)
        
        return False


class AnnotationSchema(BaseModel):
    """Complete annotation schema definition."""
    
    schema_version: str = Field(default="1.0", description="Schema version")
    data_schema: list[DataField] = Field(..., description="List of data fields to collect")
    
    def get_field(self, field_id: str) -> Optional[DataField]:
        """Get a field by its ID."""
        for field in self.data_schema:
            if field.id == field_id:
                return field
        return None
    
    def validate_annotations(self, annotations: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a set of annotations against this schema.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields
        for field in self.data_schema:
            if field.required and field.id not in annotations:
                errors.append(f"Required field '{field.id}' is missing")
        
        # Validate each annotation value
        for field_id, value in annotations.items():
            field = self.get_field(field_id)
            if field is None:
                errors.append(f"Unknown field '{field_id}'")
                continue
            
            if not field.validate_value(value):
                errors.append(f"Invalid value for field '{field_id}': {value}")
        
        return len(errors) == 0, errors
