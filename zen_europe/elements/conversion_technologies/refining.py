from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.technology.economics_of_oil_refining import (
    EconomicsOfOilRefining,
)
from zen_europe.datasets.datasets.technology.energyinst_world_energy_review import (
    EnergyInstituteWorldEnergyReview,
)
from zen_europe.datasets.datasets.technology.future_hydrogen_demand_neuwirth import (
    FutureHydrogenDemandNeuwirth,
)
from zen_europe.datasets.datasets.technology.LCA_refining import LCARefining
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology


class Refining(ConversionTechnology):
    """Class containing all data and assumptions for oil refining
    (crude oil and hydrogen to oil products)."""

    name: str = "refining"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of refining to oil.
        """
        return Attribute(name="reference_carrier", default_value=["oil"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of refining to crude oil and hydrogen.
        """
        return Attribute(
            name="input_carrier", default_value=["crude_oil", "hydrogen"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of refining to oil.
        """
        return Attribute(name="output_carrier", default_value=["oil"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of refining.

        """
        lca_ref_dataset = LCARefining(source_path=self.source_path)
        return lca_ref_dataset.get_lifetime(element=self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of refining.

        """
        if self.settings.investment.use_construction_times:
            lca_ref_dataset = LCARefining(source_path=self.source_path)
            return lca_ref_dataset.get_construction_time(element=self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of refining.

        Hydrogen demand for hydrotreating/hydrocracking is manually set to
        0.541 MWh_H2/toe of oil product, converted to a MWh/MWh basis using
        the standard MWh-to-toe conversion factor (1 MWh = 0.0859845 toe).
        """
        future_H2_dataset = FutureHydrogenDemandNeuwirth(source_path=self.source_path)
        return future_H2_dataset.get_conversion_factor_refining(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for refining.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        oil_ref_dataset = EconomicsOfOilRefining(source_path=self.source_path)
        return oil_ref_dataset.get_capex_specific(element=self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for refining.

        Manually set assuming 1.5% of investment for maintenance plus
        27.5 M USD/year for personnel (midpoint of the 15-40 M USD/year
        range), https://link.springer.com/chapter/10.1007/978-3-030-86884-0_3

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        oil_ref_dataset = EconomicsOfOilRefining(source_path=self.source_path)
        return oil_ref_dataset.get_opex_specific_fixed(element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for refining.

        Manually set to 1 USD/barrel,
        https://link.springer.com/chapter/10.1007/978-3-030-86884-0_3

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        oil_ref_dataset = EconomicsOfOilRefining(source_path=self.source_path)
        return oil_ref_dataset.get_opex_specific_variable(element=self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing refining capacity in Europe.

        Returns:
            Attribute: An Attribute object containing the existing refining capacity
                data.
        """
        if self.settings.investment.use_existing_capacities:
            energyinst_dataset = EnergyInstituteWorldEnergyReview(
                source_path=self.source_path
            )
            return energyinst_dataset.get_capacity_existing_refining(self)
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
        Sets the maximum diffusion rate of refining.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
