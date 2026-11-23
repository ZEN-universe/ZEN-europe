from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.industrial_waste_heat import (
    IndustrialWasteHeat,
)
from zen_europe.datasets.datasets.carrier.material_economics import MaterialEconomics
from zen_europe.datasets.datasets.technology.cement_production_gardarsdottir import (
    CementProductionGardarsdottir,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, ConversionTechnology


class CementProduction(ConversionTechnology):
    """Class containing all data and assumptions for cement production (clinker
    kilns)."""

    name: str = "cement_production"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of cement production to clinker.
        """
        return Attribute(
            name="reference_carrier", default_value=["clinker"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of cement production to cement fuel and
        electricity.
        """
        return Attribute(
            name="input_carrier",
            default_value=["cement_fuel", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of cement production to clinker and the waste heat of
        the kiln.
        """
        return Attribute(
            name="output_carrier",
            default_value=["clinker", *self.settings.operation.waste_heat_carriers],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of cement production.

        """
        cement_dataset = CementProductionGardarsdottir(source_path=self.source_path)
        return cement_dataset.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of cement production.

        """
        if self.settings.investment.use_construction_times:
            cement_dataset = CementProductionGardarsdottir(source_path=self.source_path)
            return cement_dataset.get_construction_time(self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of cement production, including the waste heat
        of the kiln.

        """
        waste_heat_dataset = IndustrialWasteHeat(self.settings, self.source_path)
        return waste_heat_dataset.get_conversion_factor_cement_production(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """
        Sets the carbon intensity of cement production.

        Returns:
            Attribute: An Attribute object containing the carbon intensity data.
        """
        material_economics_dataset = MaterialEconomics(source_path=self.source_path)
        return material_economics_dataset.get_clinker_carbon_intensity(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific conversion capital expenditure (capex) for cement
        production.

        Returns:
            Attribute: An Attribute object containing the specific conversion capex
                data.
        """
        cement_dataset = CementProductionGardarsdottir(source_path=self.source_path)
        return cement_dataset.get_capex_specific(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for cement
        production.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        cement_dataset = CementProductionGardarsdottir(source_path=self.source_path)
        return cement_dataset.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for cement
        production.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        cement_dataset = CementProductionGardarsdottir(source_path=self.source_path)
        return cement_dataset.get_opex_specific_variable(self)
