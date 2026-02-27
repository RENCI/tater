"""Tater widgets for building annotation interfaces."""
from tater.widgets.base import TaterWidget
from tater.widgets.segmented_control import SegmentedControlWidget
from tater.widgets.radio_group import RadioGroupWidget
from tater.widgets.checkbox import CheckboxWidget
from tater.widgets.text_input import TextInputWidget

from tater.widgets.group import GroupWidget
from tater.widgets.listable import ListableWidget
from tater.widgets.multiselect import MultiSelectWidget
from tater.widgets.number_input import NumberInputWidget
from tater.widgets.chip_group import ChipGroupWidget

__all__ = [
    "TaterWidget",
    "SegmentedControlWidget",
    "RadioGroupWidget",
    "CheckboxWidget",
    "TextInputWidget",
    "GroupWidget",
    "ListableWidget",
    "MultiSelectWidget",
    "NumberInputWidget",
    "ChipGroupWidget",
]
