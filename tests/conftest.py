"""Shared fixtures for tater tests."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

import pytest

from tater import SpanAnnotation


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog", "fish"]] = None
    neutered: Optional[bool] = None
    indoor: Optional[bool] = None
    breed: Optional[str] = None


class Address(BaseModel):
    city: Optional[str] = None
    zip: Optional[str] = None


class Owner(BaseModel):
    name: Optional[str] = None
    address: Optional[Address] = None


class Finding(BaseModel):
    label: Optional[Literal["positive", "negative", "uncertain"]] = None
    evidence: List[SpanAnnotation] = Field(default_factory=list)


class Schema(BaseModel):
    pets: List[Pet] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    owner: Optional[Owner] = None
    overall: Optional[str] = None
    score: Optional[int] = None
    flags: List[Literal["urgent", "review"]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_schema():
    return Schema()


@pytest.fixture
def schema_with_pets():
    s = Schema()
    s.pets = [Pet(kind="cat", neutered=True), Pet(kind="dog")]
    return s


@pytest.fixture
def schema_with_findings():
    s = Schema()
    s.findings = [
        Finding(label="positive", evidence=[
            SpanAnnotation(start=0, end=5, text="hello", tag="Support"),
        ]),
        Finding(label="negative"),
    ]
    return s
