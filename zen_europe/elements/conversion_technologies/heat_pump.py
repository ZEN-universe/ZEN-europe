from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute


class HeatPump(ConversionTechnology):

    name: str = "heat_pump"

    def __init__(self, model: Model):
        super().__init__(model=model)

    def _set_lifetime(self) -> Attribute:
        attr = self._lifetime
        return attr

    def _set_conversion_factor(self) -> Attribute:
        attr = self._conversion_factor
        return attr

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["heat"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute(
            name="input_carrier", default_value=["electricity"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        return Attribute(name="output_carrier", default_value=["heat"], element=self)
