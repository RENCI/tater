"""Tests for _has_value — the field-completeness predicate."""
import pytest
from tater.ui.callbacks import _has_value


@pytest.mark.parametrize("value, expected", [
    # Falsy / empty
    (None,    False),
    ("",      False),
    ("   ",   False),
    ([],      False),
    # Truthy
    ("hello", True),
    ("0",     True),
    ([1],     True),
    (["a"],   True),
    # Non-None scalars that might trip up naive checks
    (0,       True),
    (0.0,     True),
    (False,   True),
    (True,    True),
])
def test_has_value(value, expected):
    assert _has_value(value) is expected
