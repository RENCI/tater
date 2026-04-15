"""Shared fixtures for tater tests."""
import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

import pytest

from tater import SpanAnnotation


# ---------------------------------------------------------------------------
# Browser driver setup — use webdriver-manager to fetch a matching chromedriver
# for the installed google-chrome, and register it via pytest_setup_options.
# ---------------------------------------------------------------------------

def pytest_setup_options():
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Install/cache the correct chromedriver and put it on PATH
    driver_path = ChromeDriverManager().install()
    os.environ["PATH"] = os.path.dirname(driver_path) + ":" + os.environ.get("PATH", "")
    return options


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


class Measurements(BaseModel):
    weight: Optional[float] = None
    range_float: Optional[list[float]] = None
    range_int: Optional[list[int]] = None
    range_str: Optional[list[str]] = None


class Schema(BaseModel):
    pets: List[Pet] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    owner: Optional[Owner] = None
    overall: Optional[str] = None
    score: Optional[int] = None
    flags: List[Literal["urgent", "review"]] = Field(default_factory=list)
    measurements: Optional[Measurements] = None
    hl_path: Optional[List[str]] = None


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
