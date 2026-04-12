from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, ConversionTechnology


class Photovoltaics(ConversionTechnology):
    """Class containing all data and assumptions for photovoltaics."""

    name: str = "photovoltaics"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of photovoltaics to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of photovoltaics to an empty list.

        This is because photovoltaics do not have an input carrier,
        as they convert solar energy directly into electricity.
        """
        return Attribute(name="input_carrier", default_value=[], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of photovoltaics to electricity.
        """
        return Attribute(
            name="output_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of photovoltaics.

        This method is currently returns the default value.
        """
        attr = self.lifetime
        return attr

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of photovoltaics.

        This method currently returns the default value.
        """
        attr = self.conversion_factor
        return attr
