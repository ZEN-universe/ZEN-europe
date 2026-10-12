from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.datasets.datasets.carrier.truck_standard_load_profiles import (
    TruckStandardLoadProfiles,
)
from zen_europe.datasets.datasets.technology.truck_technologies_icct import (
    TruckTechnologiesICCT,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


import numpy as np
from zen_creator import Attribute, Carrier, ConversionTechnology, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.statistical_pocketbook_transport import (
    StatisticalPocketbookTransport,
)


class TruckMileageDemand(DatasetCollection):
    """Extracting truck mileage demand data."""

    name = "truck_mileage_demand"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "eurostat": Eurostat(self.settings, self.source_path),
            "statistical_pocketbook_transport": StatisticalPocketbookTransport(
                self.settings, self.source_path
            ),
            "truck_standard_load_profiles": TruckStandardLoadProfiles(self.source_path),
            "truck_technologies": TruckTechnologiesICCT(self.source_path),
        }

    def get_demand(self, element: Carrier) -> Attribute:
        """
        Get the truck mileage demand for the specified element.

        """
        slp_country = self._get_hourly_demand(element=element)

        source = SourceInformation(
            description=(
                "Total truck mileage demand is derived from the Statistical Pocketbook "
                "Transport dataset, which provides data on passenger and truck mileage "
                "in the EU. The standard load profiles for trucks is obtained "
                "fromBorlaug et al. (2021). The final truck mileage demand is "
                "calculated by multiplying the total truck mileage by the weighted "
                "standard load profiles."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=slp_country,
            unit="megatkm/hour",
        )

    def _get_hourly_demand(self, element: Carrier) -> pd.DataFrame:
        """
        Get the hourly truck mileage demand for the specified element.

        """
        slp_dataset = cast(
            TruckStandardLoadProfiles, self.data["truck_standard_load_profiles"]
        )
        slp = slp_dataset.get_standard_load_profiles()
        total_demand = self._get_total_demand(element=element)
        slp_country = pd.DataFrame(
            data=np.outer(slp, total_demand),
            index=slp.index,
            columns=total_demand.index,
        )

        slp_country = slp_dataset.shift_by_timezone(slp_country)

        return slp_country

    def _get_total_demand(self, element: Carrier) -> pd.Series:
        """
        Get the total truck mileage demand for the specified element.

        """
        spt_dataset = cast(
            StatisticalPocketbookTransport,
            self.data["statistical_pocketbook_transport"],
        )
        total_demand = spt_dataset.get_total_mileage(element)
        return total_demand

    def _get_peak_demand_share(self, element: Carrier) -> pd.Series:
        """
        Get the peak demand share for the specified element.

        """
        slp_country = self._get_hourly_demand(element=element)
        total_demand = self._get_total_demand(element=element)
        peak_demand_share = (slp_country / (total_demand / 8760)).max()
        return peak_demand_share

    def get_max_load(self, element: ConversionTechnology) -> Attribute:
        """
        Get the maximum load for the specified element.

        """
        truck_mileage = element.model.carriers["truck_mileage"]
        slp_country = self._get_hourly_demand(element=truck_mileage)
        max_demand = slp_country.max()
        max_load = slp_country.div(max_demand, axis=1)
        max_load.index.name = "time"
        attr = element.max_load
        return attr.set_data(
            df=max_load,
            source=SourceInformation(
                description=(
                    "The maximum load of the truck mileage demand is calculated by "
                    "dividing the hourly truck mileage demand by the maximum hourly "
                    "demand. The hourly truck mileage demand is derived from the "
                    "Statistical Pocketbook Transport dataset and the standard load "
                    "profiles for trucks."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )
