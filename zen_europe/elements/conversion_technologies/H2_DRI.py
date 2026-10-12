from __future__ import annotations

from typing import TYPE_CHECKING

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

from zen_creator import Attribute, ConversionTechnology


class H2_DRI(ConversionTechnology):
    """Class containing all data and assumptions for hydrogen-based direct
    reduced iron (H2-DRI) primary steelmaking."""

    name: str = "H2_DRI"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of H2-DRI to primary steel.
        """
        return Attribute(
            name="reference_carrier", default_value=["primary_steel"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of H2-DRI to hydrogen, electricity and hard
        coal.
        """
        return Attribute(
            name="input_carrier",
            default_value=["hydrogen", "electricity", "hard_coal"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of H2-DRI to primary steel.
        """
        return Attribute(
            name="output_carrier", default_value=["primary_steel"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of H2-DRI.

        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of H2-DRI.

        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_conversion_factor(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for
        H2-DRI.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_opex_specific_variable(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """
        Sets the carbon intensity of H2-DRI.

        Returns:
            Attribute: An Attribute object containing the carbon intensity data.
        """
        agora_dataset = AgoraIndustrySteel(source_path=self.source_path)
        return agora_dataset.get_carbon_intensity_technology(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for H2-DRI.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        steel_woertler_dataset = SteelTechnologiesWoertler(self.source_path)
        return steel_woertler_dataset.get_capex_specific(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of H2 DRI.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
