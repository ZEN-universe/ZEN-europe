from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.clinker_data import ClinkerData
from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, RetrofittingTechnology


class CoalToCementFuel(RetrofittingTechnology):
    """Class containing all data and assumptions for coal-fired cement-kiln
    fuel supply (hard coal to fuel for cement)."""

    name: str = "coal_to_cement_fuel"
    base_technology_name: str = "cement_kiln"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of coal to cement fuel to fuel for cement.
        """
        return Attribute(
            name="reference_carrier", default_value=["fuel_for_cement"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of coal to cement fuel to hard coal.
        """
        return Attribute(
            name="input_carrier", default_value=["hard_coal"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of coal to cement fuel to fuel for cement.
        """
        return Attribute(
            name="output_carrier", default_value=["fuel_for_cement"], element=self
        )

    def _set_retrofit_reference_carrier(self) -> Attribute:
        """
        Sets the retrofit reference carrier of coal to cement fuel to fuel for
        cement.
        """
        return Attribute(
            name="retrofit_reference_carrier",
            default_value=["fuel_for_cement"],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of coal to cement fuel.
        Assume the same lifetime as cement kilns, since the fuel supply is tied to the
        cement kiln operation.
        """
        attr = self.lifetime
        cement_kiln = self.model.conversion_technologies["cement_kiln"]
        attr.set_data(
            default_value=cement_kiln.lifetime.default_value,
            unit=cement_kiln.lifetime.unit,
            source=AssumptionInformation(
                description=(
                    "The lifetime of coal to cement fuel is assumed to be the same "
                    "as the lifetime of cement kilns, since the fuel supply is tied to "
                    "the cement kiln operation."
                ),
            ),
        )
        return attr

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of coal to cement fuel.

        Hard coal is the fuel-for-cement reference fuel, so the conversion
        factor is 1.
        """
        aidres_dataset = Aidres(source_path=self.source_path)
        return aidres_dataset.get_conversion_factor_cement_fuel(self)

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        """
        Return the retrofit flow coupling factor of coal to cement fuel.

        Hard coal is the reference fuel of cement kilns and can cover the entire
        kiln fuel demand.
        """
        clinker_demand_dataset = ClinkerData(source_path=self.source_path)
        return clinker_demand_dataset.get_retrofit_flow_coupling_factor(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for coal to cement fuel.

        Coal is the reference fuel for cement kilns, so no additional retrofitting
        costs are assumed for coal to cement fuel conversion.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        attr = self.capex_specific_conversion
        attr.set_data(
            default_value=0,
            unit="Euro/GW",
            source=AssumptionInformation(
                description=(
                    "The specific capital expenditure (capex) for coal to cement fuel "
                    "is set to 0, since hard coal is the reference fuel for cement "
                    "kilns and no additional retrofitting costs are assumed for coal "
                    "to cement fuel conversion."
                ),
            ),
        )
        return attr

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of coal to cement fuel.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            clinker_demand_dataset = ClinkerData(source_path=self.source_path)
            return clinker_demand_dataset.get_capacity_existing_cement_fuel(self)
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
        Sets the maximum diffusion rate of coal to cement fuel.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
