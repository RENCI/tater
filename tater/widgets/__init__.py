"""Tater widgets for building annotation interfaces."""
from tater.widgets.base import (
    TaterWidget,
    ControlWidget,
    ContainerWidget,
    ChoiceWidget,
    MultiChoiceWidget,
    BooleanWidget,
    NumericWidget,
    TextWidget,
)
from tater.widgets.segmented_control import SegmentedControlWidget
from tater.widgets.radio_group import RadioGroupWidget
from tater.widgets.checkbox import CheckboxWidget
from tater.widgets.text_input import TextInputWidget

from tater.widgets.group import GroupWidget
from tater.widgets.repeater import RepeaterWidget, ListableWidget, TabsWidget, AccordionWidget
from tater.widgets.multiselect import MultiSelectWidget
from tater.widgets.number_input import NumberInputWidget
from tater.widgets.slider import SliderWidget
from tater.widgets.textarea import TextAreaWidget
from tater.widgets.range_slider import RangeSliderWidget
from tater.widgets.switch import SwitchWidget
from tater.widgets.chip import ChipWidget
from tater.widgets.select import SelectWidget
from tater.widgets.span import SpanAnnotationWidget, EntityType
from tater.widgets.hierarchical_label import (
    HierarchicalLabelWidget,
    HierarchicalLabelFullWidget,
    HierarchicalLabelCompactWidget,
    Node,
    build_tree,
    load_hierarchy_from_yaml,
)

__all__ = [
    "TaterWidget",
    "ControlWidget",
    "ContainerWidget",
    "ChoiceWidget",
    "MultiChoiceWidget",
    "BooleanWidget",
    "NumericWidget",
    "TextWidget",
    "SegmentedControlWidget",
    "RadioGroupWidget",
    "CheckboxWidget",
    "TextInputWidget",
    "GroupWidget",
    "RepeaterWidget",
    "ListableWidget",
    "TabsWidget",
    "AccordionWidget",
    "MultiSelectWidget",
    "NumberInputWidget",
    "SliderWidget",
    "TextAreaWidget",
    "RangeSliderWidget",
    "SwitchWidget",
    "ChipWidget",
    "SelectWidget",
    "SpanAnnotationWidget",
    "EntityType",
    "HierarchicalLabelWidget",
    "HierarchicalLabelFullWidget",
    "HierarchicalLabelCompactWidget",
    "Node",
    "build_tree",
    "load_hierarchy_from_yaml",
]
