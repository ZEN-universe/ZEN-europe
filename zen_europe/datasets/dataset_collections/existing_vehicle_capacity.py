from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

from zen_europe.datasets.dataset_collections.passenger_mileage_demand import (
    PassengerMileageDemand,
)
from zen_europe.datasets.dataset_collections.truck_mileage_demand import (
    TruckMileageDemand,
)
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.technology.passenger_cars_cox import PassengerCarsCox
from zen_europe.datasets.datasets.technology.truck_technologies_icct import (
    TruckTechnologiesICCT,
)
from zen_europe.datasets.datasets.technology.unece import UNECE

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


import numpy as np
import pandas as pd
from zen_creator import (
    Attribute,
    ConversionTechnology,
    DatasetCollection,
    SourceInformation,
)
from zen_creator.utils.settings import Settings

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import (
    account_for_decommissioned_capacity,
    format_capacity_existing,
)

# The capacity of a passenger car is the mileage it delivers per hour.
_PASSENGER_CAPEX_UNIT = "Euro/(vkm/h)"
# Passenger cars whose purchase price is dominated by the battery, and which
# therefore follow the battery cost evolution of Cox et al. (2020).
_BATTERY_CARS = ["BEV", "PHEV"]
# The year Cox et al. report their future battery cost for; it is held
# constant beyond it.
_BATTERY_COST_FUTURE_YEAR = 2040

# The fuel that each refinery output-shifting technology produces, and the
# technologies whose existing fleet burns it. A refinery has to be able to
# supply the fleet that exists today.
_OIL_CONVERSION_CONSUMERS = {
    "oil_to_gasoline_conversion": ("gasoline", ["ICE_petrol"]),
    "oil_to_diesel_conversion": ("diesel", ["ICE_diesel", "HDT_diesel"]),
}
# Shipping is assumed to run entirely on diesel. Its fuel demand is taken
# directly rather than through a fleet, so it is added separately.
_OIL_CONVERSION_WITH_SHIPPING = ["oil_to_diesel_conversion"]
# An existing fleet capacity is in millions of vehicle or tonne kilometres per
# hour, so the fuel demand per kilometre has to be scaled to give GW: a GWh/km
# factor by 1e6, a kWh/km factor by 1, since 1e6 kWh make one GWh.
_FUEL_DEMAND_SCALE = {"GWh/vkm": 1e6, "kWh/tkm": 1.0}
_OIL_CONVERSION_CAPACITY_UNIT = "GW"
# Reference carrier of the technologies whose fleet is measured in tonne
# kilometres rather than vehicle kilometres.
_TRUCK_MILEAGE = "truck_mileage"


class ExistingVehicleCapacity(DatasetCollection):
    """Extracting existing vehicle capacity data."""

    name = "existing_vehicle_capacity"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "unece": UNECE(settings=self.settings, source_path=self.source_path),
            "pass_demand": PassengerMileageDemand(
                settings=self.settings, source_path=self.source_path
            ),
            "truck_mileage": TruckMileageDemand(
                settings=self.settings, source_path=self.source_path
            ),
            "truck_technologies": TruckTechnologiesICCT(self.source_path),
            "passenger_cars": PassengerCarsCox(self.source_path),
            "eurostat": Eurostat(self.settings, self.source_path),
        }

    def get_existing_capacity_passenger(
        self, element: ConversionTechnology
    ) -> pd.Series:
        """Get the existing vehicle capacity for passenger vehicles.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the existing vehicle capacity.

        Returns:
            pd.Series: The existing vehicle capacity for passenger vehicles.
        """
        unece = cast(UNECE, self.data["unece"])
        fleet = unece.get_total_fleet()
        registrations = unece.get_registrations()
        passenger_transport_db = cast(PassengerMileageDemand, self.data["pass_demand"])
        passenger_mileage = element.model.carriers["passenger_mileage"]
        total_demand = passenger_transport_db._get_total_demand(
            element=passenger_mileage
        )
        mvkm_per_h = total_demand.sum() / fleet.iloc[:, -1].sum() / 8760  # mvkm/h
        capacity_existing = registrations * mvkm_per_h
        capacity_existing = cast(pd.DataFrame, capacity_existing.loc[element.name])
        hourly_demand = cast(pd.DataFrame, passenger_mileage.demand.df)
        peak_demand_share = (hourly_demand / (total_demand / 8760)).max()
        # adjust the existing capacity to account for the peak demand share
        capacity_existing = capacity_existing.mul(peak_demand_share, axis=0)
        data = format_capacity_existing(capacity_existing.stack().astype(float))
        return data

    def get_existing_capacity_truck(self, element: ConversionTechnology) -> pd.Series:
        """Get the existing vehicle capacity for trucks.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the existing vehicle capacity.

        Returns:
            pd.Series: The existing vehicle capacity for trucks.
        """
        unece = cast(UNECE, self.data["unece"])
        fleet_by_tech = unece.get_truck_fleet()
        fleet = unece.get_total_truck_fleet()
        # a copy, since `get_truck_registrations` is cached and the column
        # added below would otherwise accumulate on the cached frame
        registrations = unece.get_truck_registrations().copy()
        diff_fleet = (fleet_by_tech.iloc[:, -1] - registrations.sum(axis=1)).clip(
            lower=0
        )
        registrations[cast(int, registrations.columns.min()) - 1] = diff_fleet
        registrations = registrations.sort_index(axis=1)

        truck_transport_db = cast(TruckMileageDemand, self.data["truck_mileage"])
        truck_mileage = element.model.carriers["truck_mileage"]
        total_demand = truck_transport_db._get_total_demand(element=truck_mileage)
        mtkm_per_h = total_demand.sum() / fleet.iloc[:, -1].sum() / 8760  # mtkm/h
        capacity_existing = registrations * mtkm_per_h
        capacity_existing = cast(pd.DataFrame, capacity_existing.loc[element.name])
        peak_demand_share = truck_transport_db._get_peak_demand_share(
            element=truck_mileage
        )
        # adjust the existing capacity to account for the peak demand share
        capacity_existing = capacity_existing.mul(peak_demand_share, axis=0)
        capacity_existing = account_for_decommissioned_capacity(
            capacity_existing, element
        )
        data = format_capacity_existing(capacity_existing.stack())
        return data

    def get_existing_capacity_oil_conversion(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the existing capacity for the specified refinery output-shifting
        technology.

        The refinery has to be able to supply the fuel that the vehicles on the
        road today burn, so the existing capacity is the fuel demand of the
        existing fleet: the passenger cars, the heavy-duty trucks and, for
        diesel, the ships. Each fleet is converted from its mileage to a fuel
        demand with the conversion factor of the technology that burns it.

        Args:
            element (ConversionTechnology): The conversion technology element
                for which to get the existing capacity.

        Returns:
            Attribute: An Attribute object containing the existing capacity.
        """
        if element.name not in _OIL_CONVERSION_CONSUMERS:
            raise ValueError(
                f"'{element.name}' is not a refinery output-shifting "
                f"technology, expected one of {sorted(_OIL_CONVERSION_CONSUMERS)}."
            )
        fuel, consumers = _OIL_CONVERSION_CONSUMERS[element.name]

        fuel_demands = [
            self._get_fleet_fuel_demand(
                cast(ConversionTechnology, element.model.elements[consumer]), fuel
            )
            for consumer in consumers
            if consumer in element.model.elements
        ]
        if element.name in _OIL_CONVERSION_WITH_SHIPPING:
            fuel_demands.append(self._get_shipping_fuel_demand(element))
        if not fuel_demands:
            raise ValueError(
                f"None of the technologies that burn '{fuel}' ({consumers}) "
                f"is part of the model, so the existing capacity of "
                f"'{element.name}' cannot be derived."
            )

        capacity_existing = fuel_demands[0]
        for fuel_demand in fuel_demands[1:]:
            capacity_existing = capacity_existing.add(fuel_demand, fill_value=0)
        capacity_existing = capacity_existing.dropna().astype(float)
        capacity_existing.index.names = ["node", "year_construction"]
        capacity_existing.name = "capacity_existing"

        attr = element.capacity_existing
        return attr.set_data(
            df=capacity_existing,
            source=SourceInformation(
                description=(
                    f"The existing capacity of {element.name} is the "
                    f"'{fuel}' demand of the vehicles on the road today, so "
                    "that the refinery can supply the existing fleet. The "
                    f"fleet of {', '.join(consumers)} is sourced from the "
                    "UNECE dataset and converted to a fuel demand with the "
                    "conversion factor of each technology."
                    + (
                        " The shipping fuel demand of Eurostat is added, "
                        "assuming that all shipping runs on diesel."
                        if element.name in _OIL_CONVERSION_WITH_SHIPPING
                        else ""
                    )
                ),
                metadata=self.metadata,
            ),
            unit=_OIL_CONVERSION_CAPACITY_UNIT,
        )

    def _get_fleet_fuel_demand(
        self, element: ConversionTechnology, carrier: str
    ) -> pd.Series:
        """Fuel demand in GW of the existing fleet of one vehicle technology,
        per node and year of construction."""
        if (
            cast(list[str], element.reference_carrier.default_value)[0]
            == _TRUCK_MILEAGE
        ):
            fleet = self.get_existing_capacity_truck(element=element)
        else:
            fleet = self.get_existing_capacity_passenger(element=element)
        return fleet * self._get_fuel_per_kilometre(element, carrier)

    @staticmethod
    def _get_fuel_per_kilometre(element: ConversionTechnology, carrier: str) -> float:
        """Fuel demand of one vehicle per kilometre, scaled so that multiplying
        it with a fleet capacity in million kilometres per hour gives GW."""
        conversion_factors = cast(
            list[dict[str, dict[str, Any]]], element.conversion_factor.default_value
        )
        for conversion_factor in conversion_factors:
            if carrier not in conversion_factor:
                continue
            factor = conversion_factor[carrier]
            if factor["unit"] not in _FUEL_DEMAND_SCALE:
                raise ValueError(
                    f"The conversion factor of '{element.name}' is given in "
                    f"'{factor['unit']}', which cannot be scaled to GW; "
                    f"expected one of {sorted(_FUEL_DEMAND_SCALE)}."
                )
            return factor["default_value"] * _FUEL_DEMAND_SCALE[factor["unit"]]
        raise ValueError(f"'{element.name}' does not consume '{carrier}'.")

    def _get_shipping_fuel_demand(self, element: ConversionTechnology) -> pd.Series:
        """Shipping fuel demand in GW per node, assigned to the last year
        before the reference year."""
        eurostat = cast(Eurostat, self.data["eurostat"])
        demand = eurostat.get_shipping_fuel_demand()
        nodes = demand.index.intersection(element.model.config.system.set_nodes)
        demand = demand.loc[nodes] / Constants.HOURS_PER_YEAR
        demand.index = pd.MultiIndex.from_product(
            [demand.index, [element.settings.time.reference_year - 1]],
            names=["node", "year_construction"],
        )
        return demand

    def get_capex_specific_conversion_passenger(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the specific conversion CAPEX for the specified passenger car.

        The purchase price of a car is scaled to the hourly mileage it can
        deliver, which is a fraction of its average mileage: the fleet has to
        be large enough to cover the peak of the daily driving profile. The
        cars whose battery dominates their cost get a cost evolution rather
        than a single value, since the battery cost falls towards 2040.

        Args:
            element (ConversionTechnology): The conversion technology element
                for which to get the specific conversion CAPEX.

        Returns:
            Attribute: An Attribute object containing the specific conversion
            CAPEX.
        """
        cars = cast(PassengerCarsCox, self.data["passenger_cars"])
        passenger_transport_db = cast(PassengerMileageDemand, self.data["pass_demand"])
        passenger_mileage = element.model.carriers["passenger_mileage"]
        peak_demand_share = passenger_transport_db._get_peak_demand_share(
            element=passenger_mileage
        )
        capex = cars.get_cost(element, "capex")

        df: pd.DataFrame | pd.Series | None
        if not element.settings.cost.use_learning_curves:
            # without learning curves every node and year uses the default
            df = None
        elif element.name in _BATTERY_CARS:
            evolution = self._get_capex_evolution_passenger(element, cars, capex)
            nodal = 1 / peak_demand_share.dropna()
            df = pd.DataFrame(
                np.outer(evolution, nodal), index=evolution.index, columns=nodal.index
            )
            df.index.name = "year"
        else:
            df = capex / peak_demand_share.dropna()
            df.index.name = "node"
            df.name = "capex_specific_conversion"

        attr = element.capex_specific_conversion
        return attr.set_data(
            df=df,
            default_value=float(capex / peak_demand_share.mean()),
            source=SourceInformation(
                description=(
                    f"The specific conversion CAPEX of {element.name} is the "
                    "purchase price of the lower medium car of Cox et al. "
                    "(2020), taken at the manufacturing cost rather than at "
                    "the consumer price, i.e. divided by the markup factor. "
                    "It is divided by the hourly mileage of the car and "
                    "adjusted for the peak demand share. Monetary values are "
                    f"rebased from {cars.MONEY_YEAR} to "
                    f"{element.settings.time.price_year} Euro using ECB "
                    "HICP inflation."
                    + (
                        " The battery share of the price follows the battery "
                        "cost of Cox et al. from the reference year to their "
                        "2040 value and stays constant afterwards."
                        if element.name in _BATTERY_CARS
                        else ""
                    )
                ),
                metadata=self.metadata,
            ),
            unit=_PASSENGER_CAPEX_UNIT,
        )

    @staticmethod
    def _get_capex_evolution_passenger(
        element: ConversionTechnology,
        cars: PassengerCarsCox,
        capex: float,
    ) -> pd.Series:
        """Interpolate the purchase price of a battery car over the years.

        Only the battery share of the price changes; the rest of the car is
        assumed to cost the same in every year.
        """
        capex_battery_current = cars.get_cost(element, "capex_bat_cur")
        capex_battery_future = cars.get_cost(element, "capex_bat_fut")
        reference_year = element.settings.time.reference_year
        years = pd.Index(element.settings.time.years).union(
            [reference_year, _BATTERY_COST_FUTURE_YEAR]
        )

        evolution = pd.Series(index=years, dtype=float)
        evolution.at[reference_year] = capex_battery_current
        evolution.at[_BATTERY_COST_FUTURE_YEAR] = capex_battery_future
        # held constant beyond the years the battery cost is known for
        evolution = evolution.interpolate(method="index")
        return evolution + capex - capex_battery_current

    def get_capex_specific_conversion_truck(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the specific conversion CAPEX for the specified element.

        """
        hdt_dataset = cast(TruckTechnologiesICCT, self.data["truck_technologies"])
        truck_transport_db = cast(TruckMileageDemand, self.data["truck_mileage"])
        capex, source = hdt_dataset.get_capex_specific_conversion(element=element)
        truck_mileage = element.model.carriers["truck_mileage"]
        peak_demand_share = truck_transport_db._get_peak_demand_share(
            element=truck_mileage
        )
        capex = capex / peak_demand_share.mean()
        capex_df: pd.Series | None = capex
        default_value = None
        if not element.settings.cost.use_learning_curves:
            # the cost stays at the value of the reference year in all years
            default_value = float(capex.loc[element.settings.time.reference_year])
            capex_df = None
        attr = element.capex_specific_conversion
        return attr.set_data(
            default_value=default_value,
            df=capex_df,
            source=SourceInformation(
                description=(
                    f"The specific conversion CAPEX of {element.name} is sourced from "
                    f"the ICCT (2023) dataset for the 5-LH truck model ({source}). "
                    "It is obtained by dividing the total CAPEX of the truck by "
                    "the total mileage demand, adjusted for the peak demand share."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/(tkm/h)",
        )
