"""Helpers for reading/writing nested annotation values."""
from __future__ import annotations

import typing
from typing import Any

from pydantic import BaseModel


def set_model_value(model: BaseModel | dict, path: str, value: Any) -> None:
    """
    Set a value in a Pydantic model using dot notation with proper type handling.

    For paths like "pets.0.kind", creates model instances in lists as needed.
    """
    if isinstance(model, dict):
        set_nested_value(model, path, value)
        return

    keys = path.split('.')
    current = model
    navigation_stack = []  # Track (parent, key) for type inference

    # Navigate to the parent of the target field
    for i, key in enumerate(keys[:-1]):
        navigation_stack.append((current, key))

        if key.isdigit():
            # List indexing
            index = int(key)
            if not isinstance(current, list):
                raise ValueError(f"Cannot index non-list at {'.'.join(keys[:i+1])}")

            # Extend list with proper model instances
            while len(current) <= index:
                current.append(create_list_item(navigation_stack))

            current = current[index]
        else:
            # Attribute access
            next_value = getattr(current, key, None)

            if next_value is None:
                # Create the nested structure if the model field exists
                if isinstance(current, BaseModel):
                    field_info = type(current).model_fields.get(key)
                    if field_info:
                        # Unwrap Optional[X] → X
                        inner = field_info.annotation
                        origin = typing.get_origin(inner)
                        if origin is typing.Union:
                            args = [a for a in typing.get_args(inner) if a is not type(None)]
                            if len(args) == 1:
                                inner = args[0]
                        # Instantiate sub-model or create empty list
                        if isinstance(inner, type) and issubclass(inner, BaseModel):
                            setattr(current, key, inner())
                        elif typing.get_origin(inner) is list:
                            setattr(current, key, [])
                        else:
                            raise ValueError(f"Cannot create field {key}")
                        next_value = getattr(current, key)
                    else:
                        raise ValueError(f"Field {key} not in model")
                else:
                    raise ValueError("Cannot navigate through non-model")
            current = next_value

    # Now set the final value
    final_key = keys[-1]

    if final_key.isdigit():
        # Setting a list element
        index = int(final_key)
        if not isinstance(current, list):
            raise ValueError("Cannot index non-list")
        while len(current) <= index:
            current.append(None)
        current[index] = value
    else:
        # Setting a model/dict attribute
        if isinstance(current, BaseModel):
            setattr(current, final_key, value)
        elif isinstance(current, dict):
            current[final_key] = value
        else:
            raise ValueError(f"Cannot set attribute on {type(current)}")


def create_list_item(navigation_stack: list) -> Any:
    """
    Determine what type of object should be appended to a list.

    Walks the navigation stack in reverse to find the nearest list-typed field
    so that nested lists (e.g. findings.0.evidence.0) resolve the correct item
    type at each level rather than always using the outermost field.
    """
    for model, key in reversed(navigation_stack):
        if not isinstance(model, BaseModel):
            continue
        field_info = type(model).model_fields.get(key)
        if field_info is None:
            continue
        ann = field_info.annotation
        # Unwrap Optional[X]
        origin = typing.get_origin(ann)
        if origin is typing.Union:
            args = [a for a in typing.get_args(ann) if a is not type(None)]
            if len(args) == 1:
                ann = args[0]
        if typing.get_origin(ann) is list:
            item_type = typing.get_args(ann)[0]
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                try:
                    return item_type()
                except Exception:
                    return {}
    return {}  # Fallback to dict


def get_model_value(model: BaseModel | dict, path: str) -> Any:
    """
    Get a value from a Pydantic model or dict using dot notation.

    For Pydantic models, uses getattr.
    """
    if isinstance(model, dict):
        return get_nested_value(model, path)

    keys = path.split('.')
    current = model

    for key in keys:
        if current is None:
            return None

        if key.isdigit():
            # List index
            index = int(key)
            if isinstance(current, list):
                current = current[index] if index < len(current) else None
            else:
                return None
        else:
            # Object attribute - use getattr for Pydantic
            if isinstance(current, BaseModel):
                current = getattr(current, key, None)
            elif isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                return None
            else:
                return None

    return current


def get_nested_value(obj: Any, path: str) -> Any:
    """Get a value from a nested structure using dot notation (e.g., 'pets.0.kind')."""
    keys = path.split('.')
    current = obj

    for key in keys:
        if current is None:
            return None

        if isinstance(current, BaseModel):
            current = getattr(current, key, None)
        elif isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                index = int(key)
                current = current[index] if index < len(current) else None
            except (ValueError, IndexError):
                return None
        else:
            return None

    return current


def set_nested_value(obj: dict, path: str, value: Any) -> None:
    """Set a value in a nested dict structure using dot notation (e.g., 'pets.0.kind')."""
    keys = path.split('.')
    current = obj

    for i, key in enumerate(keys[:-1]):
        if isinstance(current, list):
            index = int(key)
            while len(current) <= index:
                current.append({})
            current = current[index]
        else:
            if key not in current:
                next_key = keys[i + 1]
                if next_key.isdigit():
                    current[key] = []
                else:
                    current[key] = {}
            current = current[key]
            if isinstance(current, list):
                next_key = keys[i + 1]
                if next_key.isdigit():
                    index = int(next_key)
                    while len(current) <= index:
                        current.append({})

    final_key = keys[-1]
    if isinstance(current, list):
        index = int(final_key)
        while len(current) <= index:
            current.append(None)
        current[index] = value
    else:
        current[final_key] = value
