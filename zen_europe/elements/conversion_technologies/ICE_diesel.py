from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.existing_vehicle_capacity import (
    ExistingVehicleCapacity,
)
from zen_europe.datasets.dataset_collections.passenger_mileage_demand import (
    PassengerMileageDemand,
)
from zen_europe.datasets.datasets.technology.passenger_cars_cox import PassengerCarsCox
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class ICE_diesel(ConversionTechnology):
    """Class containing all data and assumptions for diesel internal
    combustion engine passenger vehicles."""

    name: str = "ICE_diesel"

    def __init__(self, model: Model, power_unit: str = "megavkm/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of ICE diesel to passenger mileage.
        """
        return Attribute(
            name="reference_carrier", default_value=["passenger_mileage"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of ICE diesel to diesel.
        """
        return Attribute(name="input_carrier", default_value=["diesel"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of ICE diesel to passenger mileage.
        """
        return Attribute(
            name="output_carrier", default_value=["passenger_mileage"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of ICE diesel.

        """
        passenger_cars = PassengerCarsCox(source_path=self.source_path)
        return passenger_cars.get_lifetime(element=self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of ICE diesel.

        """
        passenger_cars = PassengerCarsCox(source_path=self.source_path)
        return passenger_cars.get_conversion_factor(element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable OPEX of ICE diesel.

        """
        passenger_cars = PassengerCarsCox(source_path=self.source_path)
        return passenger_cars.get_opex_specific_variable(element=self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific conversion CAPEX of ICE diesel.

        """
        vehicle_capacity = ExistingVehicleCapacity(
            settings=self.model.settings, source_path=self.source_path
        )
        return vehicle_capacity.get_capex_specific_conversion_passenger(element=self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of ICE diesel.

        """
        if self.settings.investment.use_existing_capacities:
            vehicle_capacity = ExistingVehicleCapacity(
                settings=self.model.settings, source_path=self.source_path
            )
            ex_cap = vehicle_capacity.get_existing_capacity_passenger(element=self)
            attr = self.capacity_existing
            return attr.set_data(
                df=ex_cap,
                source=SourceInformation(
                    description=(
                        "The existing capacity of ICE diesel is calculated from the "
                        "existing fleet of ICE diesel vehicles and the total passenger "
                        "mileage demand. The existing fleet is sourced from the UNECE "
                        "dataset, and the total passenger mileage demand is sourced "
                        "from the PassengerMileageDemand dataset. The capacity is "
                        "corrected for the peak demand share."
                    ),
                    metadata=vehicle_capacity.metadata,
                ),
                unit="megavkm/h",
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
        Sets the maximum load of ICE diesel.

        """
        passenger_transport_db = PassengerMileageDemand(
            settings=self.model.settings, source_path=self.source_path
        )
        return passenger_transport_db.get_max_load(element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of ICE diesel.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
