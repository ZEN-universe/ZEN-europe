from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.steel_demand import SteelDemand
from zen_europe.datasets.datasets.technology.agora_industry_steel import (
    AgoraIndustrySteel,
)
from zen_europe.datasets.datasets.technology.steel_technologies_woertler import (
    SteelTechnologiesWoertler,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology


class BF_BOF(ConversionTechnology):
    """Class containing all data and assumptions for the blast furnace /
    basic oxygen furnace (BF-BOF) primary steelmaking route."""

    name: str = "BF_BOF"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of BF-BOF to primary steel.
        """
        return Attribute(
            name="reference_carrier", default_value=["primary_steel"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of BF-BOF to hard coal.
        """
        return Attribute(
            name="input_carrier", default_value=["hard_coal"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of BF-BOF to primary steel.
        """
        return Attribute(
            name="output_carrier", default_value=["primary_steel"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of BF-BOF.

        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of BF-BOF.

        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_conversion_factor(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for BF-BOF.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_opex_specific_variable(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for BF-BOF.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        steel_woertler_dataset = SteelTechnologiesWoertler(self.source_path)
        return steel_woertler_dataset.get_capex_specific(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """
        Sets the carbon intensity of BF-BOF.

        Returns:
            Attribute: An Attribute object containing the carbon intensity data.
        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_carbon_intensity_technology(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of BF-BOF.

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

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of BF BOF.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
