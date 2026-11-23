from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import Attribute, Carrier, ConversionTechnology, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.bfs_passenger_transport import (
    BFSPassengerTransport,
)
from zen_europe.datasets.datasets.carrier.dft_road_traffic import DfTRoadTraffic
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.jrc_idees import JRCIDEES
from zen_europe.datasets.datasets.carrier.ssb_road_traffic import SSBRoadTraffic
from zen_europe.datasets.datasets.carrier.standard_load_profiles import (
    StandardLoadProfiles,
)
from zen_europe.utils.constants import Constants


class PassengerMileageDemand(DatasetCollection):
    """Extracting passenger mileage demand data."""

    name = "passenger_mileage_demand"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "eurostat": Eurostat(self.settings, self.source_path),
            "jrc_idees": JRCIDEES(self.source_path),
            "dft_road_traffic": DfTRoadTraffic(self.source_path),
            "bfs_passenger_transport": BFSPassengerTransport(self.source_path),
            "ssb_road_traffic": SSBRoadTraffic(self.source_path),
            "standard_load_profiles": StandardLoadProfiles(self.source_path),
        }

    def get_demand(self, element: Carrier) -> Attribute:
        """
        Get the passenger mileage demand for the specified element.

        """
        slp = self._get_hourly_demand(element)

        source = SourceInformation(
            description=(
                "Total passenger mileage demand is the vehicle-km driven by passenger "
                "cars in the time series year, from JRC-IDEES for the EU27 countries, "
                "DfT table TRA0101 (cars and taxis, Great Britain) for the UK, BFS "
                "table T 11.4.1.1 for CH and SSB table 12575 for NO. The standard load "
                "profiles for urban, suburban, and rural areas are obtained from the "
                "Standard Load Profiles dataset, which provides hourly load profiles "
                "for different types of days and region types. The final passenger "
                "mileage demand is calculated by multiplying the total passenger "
                "mileage by the weighted standard load profiles based on the share of "
                "the population in each region type."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=slp,
            unit="megavkm/hour",
        )

    def _get_hourly_demand(self, element: Carrier) -> pd.DataFrame:
        """
        Get the hourly passenger mileage demand for the specified element.

        """
        # get urbanization data from Eurostat dataset
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        share_regions = eurostat_dataset.get_population_by_urbanization()
        time_series_year = element.settings.time.time_series_year
        share_regions = share_regions[time_series_year].unstack()
        common_nodes = pd.Index(share_regions.columns).intersection(
            set(element.model.config.system.set_nodes)
        )
        share_regions = share_regions.loc[:, common_nodes]
        share_regions = share_regions.rename(
            index={"cities": "urban", "towns_and_suburbs": "suburban", "rural": "rural"}
        )
        # add load profiles
        slp_dataset = cast(StandardLoadProfiles, self.data["standard_load_profiles"])
        slp = slp_dataset.get_standard_load_profiles(share_regions, element)
        # total demand
        total_demand = self._get_total_demand(element)

        slp = slp.div(slp.sum(axis=0)) * total_demand
        # shift by timezone
        slp = slp_dataset.shift_by_timezone(slp)
        return slp

    def _get_peak_demand_share(self, element: Carrier) -> pd.Series:
        """
        Get the peak demand share for the specified element.

        """
        slp = self._get_hourly_demand(element=element)
        total_demand = self._get_total_demand(element=element)
        peak_demand_share = (slp / (total_demand / Constants.HOURS_PER_YEAR)).max()
        return peak_demand_share

    def get_max_load(self, element: ConversionTechnology) -> Attribute:
        """
        Get the maximum load for the specified element.

        """
        passenger_mileage = element.model.carriers["passenger_mileage"]
        slp = self._get_hourly_demand(element=passenger_mileage)
        max_demand = slp.max()
        max_load = slp.div(max_demand, axis=1)
        max_load.index.name = "time"
        attr = element.max_load
        return attr.set_data(
            df=max_load,
            source=SourceInformation(
                description=(
                    "The maximum load of the passenger mileage demand is "
                    "calculated by dividing the hourly passenger mileage "
                    "demand by the maximum hourly demand. The hourly passenger "
                    "mileage demand is derived from the vehicle-km driven by "
                    "passenger cars (JRC-IDEES, DfT, BFS, SSB) and the standard "
                    "load profiles for urban, suburban and rural areas."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )

    def _get_total_demand(self, element: Carrier) -> pd.Series:
        """
        Get the total passenger mileage demand (million vkm per year).

        The vehicle-km driven by passenger cars in the time series year: JRC-IDEES
        for the EU27, national statistics for the UK, CH and NO.
        """
        year = element.settings.time.time_series_year
        jrc_idees = cast(JRCIDEES, self.data["jrc_idees"])
        dft = cast(DfTRoadTraffic, self.data["dft_road_traffic"])
        bfs = cast(BFSPassengerTransport, self.data["bfs_passenger_transport"])
        ssb = cast(SSBRoadTraffic, self.data["ssb_road_traffic"])
        national = {
            "UK": dft.get_passenger_car_vehicle_km(year),
            "CH": bfs.get_passenger_car_vehicle_km(year),
            "NO": ssb.get_passenger_car_vehicle_km(year),
        }
        total_demand = pd.concat(
            [jrc_idees.get_passenger_car_vehicle_km(year), pd.Series(national)]
        )
        total_demand = total_demand.loc[element.model.config.system.set_nodes]
        total_demand.index.name = "node"
        total_demand.name = "demand"
        return total_demand
