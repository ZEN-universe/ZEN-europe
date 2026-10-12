from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.methanol_demand import MethanolDemand
from zen_europe.datasets.datasets.technology.methanol_production_collodi import (
    MethanolProductionCollodi,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology


class MethanolFromNaturalGas(ConversionTechnology):
    """Class containing all data and assumptions for methanol production
    from natural gas."""

    name: str = "methanol_from_natural_gas"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of methanol from natural gas to methanol.
        """
        return Attribute(
            name="reference_carrier", default_value=["methanol"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of methanol from natural gas to natural gas
        and electricity.
        """
        return Attribute(
            name="input_carrier",
            default_value=["natural_gas", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of methanol from natural gas to methanol.
        """
        return Attribute(
            name="output_carrier", default_value=["methanol"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of methanol from natural gas.

        """
        methanol_production_dataset = MethanolProductionCollodi(
            source_path=self.source_path
        )
        return methanol_production_dataset.get_lifetime(element=self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of methanol from natural gas.

        """
        if self.settings.investment.use_construction_times:
            methanol_production_dataset = MethanolProductionCollodi(
                source_path=self.source_path
            )
            return methanol_production_dataset.get_construction_time(element=self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of methanol from natural gas.

        """
        methanol_production_dataset = MethanolProductionCollodi(
            source_path=self.source_path
        )
        return methanol_production_dataset.get_conversion_factor(element=self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific conversion CAPEX of methanol from natural gas.

        """
        methanol_production_dataset = MethanolProductionCollodi(
            source_path=self.source_path
        )
        return methanol_production_dataset.get_capex_specific(element=self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed OPEX of methanol from natural gas.

        """
        methanol_production_dataset = MethanolProductionCollodi(
            source_path=self.source_path
        )
        return methanol_production_dataset.get_opex_specific_fixed(element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable OPEX of methanol from natural gas.

        """
        methanol_production_dataset = MethanolProductionCollodi(
            source_path=self.source_path
        )
        return methanol_production_dataset.get_opex_specific_variable(element=self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of methanol from natural gas.

        """
        if self.settings.investment.use_existing_capacities:
            methanol_demand_dataset = MethanolDemand(source_path=self.source_path)
            return methanol_demand_dataset.get_capacity_existing(element=self)
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
        Sets the maximum diffusion rate of methanol from natural gas.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
