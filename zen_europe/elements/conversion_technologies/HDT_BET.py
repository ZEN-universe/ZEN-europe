from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.existing_vehicle_capacity import (
    ExistingVehicleCapacity,
)
from zen_europe.datasets.dataset_collections.truck_mileage_demand import (
    TruckMileageDemand,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)
from zen_europe.datasets.datasets.technology.truck_technologies_icct import (
    TruckTechnologiesICCT,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class HDT_BET(ConversionTechnology):
    """Class containing all data and assumptions for battery electric
    heavy-duty trucks."""

    name: str = "HDT_BET"

    def __init__(self, model: Model, power_unit: str = "megatkm/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of HDT BET to truck mileage.
        """
        return Attribute(
            name="reference_carrier", default_value=["truck_mileage"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of HDT BET to electricity.
        """
        return Attribute(
            name="input_carrier", default_value=["electricity"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of HDT BET to truck mileage.
        """
        return Attribute(
            name="output_carrier", default_value=["truck_mileage"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of HDT BET.

        """
        hdt_dataset = TruckTechnologiesICCT(source_path=self.source_path)
        return hdt_dataset.get_lifetime(element=self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of HDT BET.

        """
        hdt_dataset = TruckTechnologiesICCT(source_path=self.source_path)
        return hdt_dataset.get_conversion_factor(element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable OPEX of HDT BET.

        """
        hdt_dataset = TruckTechnologiesICCT(source_path=self.source_path)
        return hdt_dataset.get_opex_specific_variable(element=self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific conversion CAPEX of HDT BET.

        """
        vehicle_capacity = ExistingVehicleCapacity(
            settings=self.model.settings, source_path=self.source_path
        )
        return vehicle_capacity.get_capex_specific_conversion_truck(element=self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of HDT BET.

        """
        if self.settings.investment.use_existing_capacities:
            vehicle_capacity = ExistingVehicleCapacity(
                settings=self.model.settings, source_path=self.source_path
            )
            ex_cap = vehicle_capacity.get_existing_capacity_truck(element=self)
            attr = self.capacity_existing
            return attr.set_data(
                df=ex_cap,
                source=SourceInformation(
                    description=(
                        "The existing capacity of HDT BET is calculated from the "
                        "existing fleet of HDT BET vehicles and the total truck "
                        "mileage demand. The existing fleet is sourced from the UNECE "
                        "dataset, and the total truck mileage demand is sourced from "
                        "the TruckMileageDemand dataset. The capacity is corrected for "
                        "the peak demand share."
                    ),
                    metadata=vehicle_capacity.metadata,
                ),
                unit="megatkm/h",
            )
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

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load of HDT BET.

        """
        truck_transport_db = TruckMileageDemand(
            settings=self.model.settings, source_path=self.source_path
        )

        return truck_transport_db.get_max_load(element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of HDT BET.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
