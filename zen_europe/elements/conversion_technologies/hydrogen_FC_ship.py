from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.technology.shipping_technologies_korberg import (
    ShippingTechnologiesKorberg,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, ConversionTechnology, SourceInformation

from zen_europe.utils.constants import Constants


class HydrogenFCShip(ConversionTechnology):
    """Class containing all data and assumptions for hydrogen fuel cell
    ships."""

    name: str = "hydrogen_FC_ship"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of hydrogen FC ships to shipping.
        """
        return Attribute(
            name="reference_carrier", default_value=["shipping"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of hydrogen FC ships to hydrogen and
        electricity (for liquefaction).
        """
        return Attribute(
            name="input_carrier",
            default_value=["hydrogen", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of hydrogen FC ships to shipping.
        """
        return Attribute(
            name="output_carrier", default_value=["shipping"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of hydrogen FC ships.

        """
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        return korberg_dataset.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of hydrogen FC ships.

        The electricity input accounts for the liquefaction energy demand
        of hydrogen (6.78 kWh/kg, relative to a 33.33 kWh/kg hydrogen
        lower heating value).
        """
        attr = self.conversion_factor
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        cf_dict = korberg_dataset.get_shipping_conversion_factors(self)
        cf = [
            {carrier: {"default_value": value, "unit": "GWh/GWh"}}
            for carrier, value in cf_dict.items()
        ]
        source = SourceInformation(
            description=(
                "The conversion factor of hydrogen FC ships is obtained "
                "from Korberg et al. (2021). The electricity input accounts for the "
                "liquefaction energy demand of hydrogen."
            ),
            metadata=korberg_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for
        hydrogen FC ships.

        The fuel distribution cost (Euro/GJ) is converted to a Euro/MWh
        cost of transported shipping service using the hydrogen-per-service
        conversion factor.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        attr = self.opex_specific_variable
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        cf_dict = korberg_dataset.get_shipping_conversion_factors(self)
        fuel_per_service = cf_dict["hydrogen"]
        gj_to_mwh = Constants.GJ_PER_MWH
        vopex = (
            korberg_dataset.get_fuel_distribution_cost(self)
            * gj_to_mwh
            * fuel_per_service
        )
        attr.set_data(
            default_value=vopex,
            unit="Euro/MWh",
            source=SourceInformation(
                description=(
                    "The variable opex of hydrogen FC ships is manually "
                    "derived from the fuel distribution cost, "
                    "based on Korberg et al. (2021)."
                ),
                metadata=korberg_dataset.metadata,
            ),
        )
        return attr

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load for hydrogen FC ships.

        Ships are assumed to operate at 75% of nominal capacity for 5280
        hours per year, based on Korberg et al. (2021).

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        attr = korberg_dataset.get_max_load(self)
        return attr

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for hydrogen FC ships.

        The capex is obtained from Korberg et al. (2021) and is expressed in Euro/kW.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        attr = self.capex_specific_conversion
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        capex, description = korberg_dataset.get_capex_specific(self)
        attr.set_data(
            default_value=capex,
            unit="Euro/kW",
            source=SourceInformation(
                description=(
                    "The specific capex of hydrogen FC ships is obtained "
                    "from Korberg et al. (2021). The selected technology is: "
                    f"{description}."
                ),
                metadata=korberg_dataset.metadata,
            ),
        )
        return attr

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for hydrogen FC ships.

        The fixed opex is obtained from Korberg et al. (2021)
        and is expressed in Euro/kW.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        attr = self.opex_specific_fixed
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        fixed_opex = korberg_dataset.get_opex_fixed(self)
        attr.set_data(
            default_value=fixed_opex,
            unit="Euro/kW",
            source=SourceInformation(
                description=(
                    "The specific fixed opex of hydrogen FC ships is obtained "
                    "from Korberg et al. (2021)."
                ),
                metadata=korberg_dataset.metadata,
            ),
        )
        return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of hydrogen FC ship.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
