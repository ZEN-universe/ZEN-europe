from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.steel_demand import SteelDemand
from zen_europe.datasets.datasets.technology.agora_industry_steel import (
    AgoraIndustrySteel,
)
from zen_europe.datasets.datasets.technology.steel_technologies_woertler import (
    SteelTechnologiesWoertler,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology


class EAF(ConversionTechnology):
    """Class containing all data and assumptions for the electric arc
    furnace (EAF) secondary steelmaking route."""

    name: str = "EAF"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of EAF to secondary steel.
        """
        return Attribute(
            name="reference_carrier", default_value=["secondary_steel"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of EAF to electricity and hard coal.
        """
        return Attribute(
            name="input_carrier",
            default_value=["electricity", "hard_coal"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of EAF to secondary steel.
        """
        return Attribute(
            name="output_carrier", default_value=["secondary_steel"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of EAF.

        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of EAF.

        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_conversion_factor(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for EAF.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_opex_specific_variable(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """
        Sets the carbon intensity of EAF.

        Returns:
            Attribute: An Attribute object containing the carbon intensity data.
        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_carbon_intensity_technology(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for EAF.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        steel_woertler_dataset = SteelTechnologiesWoertler(self.source_path)
        return steel_woertler_dataset.get_capex_specific(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of EAF.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            steel_demand_dataset = SteelDemand(source_path=self.source_path)
            return steel_demand_dataset.get_capacity_existing(self)
        else:
            attr = self.capacity_existing
            attr.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description=("We do not consider existing capacities."),
                ),
            )
            return attr
