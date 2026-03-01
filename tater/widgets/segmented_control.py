"""SegmentedControl widget for single-choice annotations."""
import dash_mantine_components as dmc

from .base import ChoiceWidget


class SegmentedControlWidget(ChoiceWidget):
    """Widget for selecting from a list of mutually exclusive options."""

    def component(self) -> dmc.SegmentedControl:
        data = [{"label": opt, "value": opt} for opt in self.options]
        return dmc.SegmentedControl(
            id=self.component_id,
            data=data,
            value=self.default,
            fullWidth=True,
        )

    def to_python_type(self) -> type:
        return str
