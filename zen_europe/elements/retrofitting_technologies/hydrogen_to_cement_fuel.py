from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.clinker_data import ClinkerData
from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.technology.ecra_technology_papers import (
    ECRATechnologyPapers,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, RetrofittingTechnology


class HydrogenToCementFuel(RetrofittingTechnology):
    """Class containing all data and assumptions for hydrogen-fired
    cement-kiln fuel supply (hydrogen to fuel for cement)."""

    name: str = "hydrogen_to_cement_fuel"
    base_technology_name: str = "cement_kiln"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of hydrogen to cement fuel to fuel for
        cement.
        """
        return Attribute(
            name="reference_carrier", default_value=["fuel_for_cement"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of hydrogen to cement fuel to hydrogen.
        """
        return Attribute(name="input_carrier", default_value=["hydrogen"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of hydrogen to cement fuel to fuel for cement.
        """
        return Attribute(
            name="output_carrier", default_value=["fuel_for_cement"], element=self
        )

    def _set_retrofit_reference_carrier(self) -> Attribute:
        """
        Sets the retrofit reference carrier of hydrogen to cement fuel to fuel
        for cement.
        """
        return Attribute(
            name="retrofit_reference_carrier",
            default_value=["fuel_for_cement"],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of hydrogen to cement fuel.

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
                    "The lifetime of hydrogen to cement fuel is assumed to be the same "
                    "as the lifetime of cement kilns, since the fuel supply is tied to "
                    "the cement kiln operation."
                ),
            ),
        )
        return attr

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of hydrogen to cement fuel.

        """
        aidres_dataset = Aidres(source_path=self.source_path)
        return aidres_dataset.get_conversion_factor_cement_fuel(self)

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        """
        Return the retrofit flow coupling factor of hydrogen to cement fuel.

        Hydrogen can cover at most 10% of the kiln fuel demand.
        """
        clinker_demand_dataset = ClinkerData(source_path=self.source_path)
        return clinker_demand_dataset.get_retrofit_flow_coupling_factor(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for hydrogen to
        cement fuel.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        ecra_dataset = ECRATechnologyPapers(source_path=self.source_path)
        return ecra_dataset.get_capex_specific_retrofitting(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of hydrogen to cement fuel.

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
        Sets the maximum diffusion rate of hydrogen to cement fuel.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
