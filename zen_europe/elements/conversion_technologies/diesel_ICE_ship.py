from __future__ import annotations

from typing import TYPE_CHECKING, cast

from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.technology.shipping_technologies_korberg import (
    ShippingTechnologiesKorberg,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)
from zen_europe.utils.utils import (
    account_for_decommissioned_capacity,
    format_capacity_existing,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)

from zen_europe.utils.constants import Constants


class DieselICEShip(ConversionTechnology):
    """Class containing all data and assumptions for diesel internal
    combustion engine ships."""

    name: str = "diesel_ICE_ship"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of diesel ICE ships to shipping.
        """
        return Attribute(
            name="reference_carrier", default_value=["shipping"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of diesel ICE ships to diesel.
        """
        return Attribute(name="input_carrier", default_value=["diesel"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of diesel ICE ships to shipping.
        """
        return Attribute(
            name="output_carrier", default_value=["shipping"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of diesel ICE ships.

        """
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        return korberg_dataset.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of diesel ICE ships.

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
                "The conversion factor of diesel ICE ships is obtained "
                "from Korberg et al. (2021)."
            ),
            metadata=korberg_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for
        diesel ICE ships.

        The fuel distribution cost (Euro/GJ) is converted to a Euro/MWh
        cost of transported shipping service using the fuel-per-service
        conversion factor.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        attr = self.opex_specific_variable
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        cf_dict = korberg_dataset.get_shipping_conversion_factors(self)
        fuel_per_service = cf_dict["diesel"]
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
                    "The variable opex of diesel ICE ships is manually "
                    "derived from the fuel distribution cost, "
                    "based on Korberg et al. (2021)."
                ),
                metadata=korberg_dataset.metadata,
            ),
        )
        return attr

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load for diesel ICE ships.

        Ships are assumed to operate at 75% of nominal capacity for 5280
        hours per year, based on Korberg et al. (2021).

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        korberg_dataset = ShippingTechnologiesKorberg(source_path=self.source_path)
        attr = korberg_dataset.get_max_load(self)
        return attr

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for diesel ICE ships.

        Derived from Eurostat shipping fuel demand, divided by the diesel
        conversion factor, assuming that all shipping fuel demand is
        currently served by diesel ships.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            eurostat_dataset = Eurostat(
                settings=self.settings, source_path=self.source_path
            )
            shipping_fuel_demand = eurostat_dataset.get_shipping_fuel_demand()
            common_nodes = shipping_fuel_demand.index.intersection(
                self.model.config.system.set_nodes
            )
            demand = shipping_fuel_demand.loc[common_nodes] / Constants.HOURS_PER_YEAR
            max_load = cast(float, self.max_load.default_value)
            cf_dict = cast(
                list[dict[str, dict[str, float]]], self.conversion_factor.default_value
            )
            diesel_cf = next(
                entry["diesel"]["default_value"]
                for entry in cf_dict
                if "diesel" in entry
            )
            capacity_existing = demand / diesel_cf / max_load

            capacity_existing.index.name = "node"
            capacity_existing.name = self.settings.time.reference_year - 1
            capacity_frame = account_for_decommissioned_capacity(
                capacity_existing.to_frame(), self
            )
            capacity_existing = format_capacity_existing(capacity_frame)
            attr = self.capacity_existing
            source = SourceInformation(
                description=(
                    "The existing capacity of diesel ICE ships is derived from "
                    "the Eurostat shipping fuel demand, divided by the diesel "
                    "conversion factor, assuming that all current shipping "
                    "fuel demand is served by diesel ICE ships."
                ),
                metadata=eurostat_dataset.metadata,
            )
            attr.set_data(df=capacity_existing, source=source, unit="GW")
            return attr
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

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for diesel ICE ships.

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
                    "The specific capex of diesel ICE ships is obtained "
                    "from Korberg et al. (2021). The selected technology is: "
                    f"{description}."
                ),
                metadata=korberg_dataset.metadata,
            ),
        )
        return attr

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for diesel ICE ships.

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
                    "The specific fixed opex of diesel ICE ships is obtained "
                    "from Korberg et al. (2021)."
                ),
                metadata=korberg_dataset.metadata,
            ),
        )
        return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of diesel ICE ship.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
