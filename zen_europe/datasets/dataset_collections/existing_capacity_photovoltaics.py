from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Technology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.technology.irena_solar_capacity import (
    IRENASolarCapacity,
)
from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
)
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
)


class ExistingCapacityPhotovoltaics(DatasetCollection):
    """Existing capacity of utility-scale and rooftop photovoltaics.

    IRENA reports the total photovoltaic capacity per country, PowerPlantMatching
    the individual plants. PowerPlantMatching lists every German plant of the
    Marktstammdatenregister, but hardly any plant below 1 MW elsewhere, so only
    plants of at least 1 MW count as utility-scale. Rooftop photovoltaics is the
    remainder of the IRENA total.
    """

    name = "existing_capacity_photovoltaics"

    MIN_UTILITY_CAPACITY_MW = 1.0

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "irena": IRENASolarCapacity(self.source_path),
            "powerplantmatching": PowerPlantMatching(self.source_path),
        }

    def get_capacity_existing(self, element: Technology) -> Attribute:
        """Get the existing capacity of utility-scale or rooftop photovoltaics."""
        if element.name == "photovoltaics_utility":
            data = self._get_utility(element)
            description = (
                "The existing capacity of utility-scale photovoltaics is the "
                "capacity of the PowerPlantMatching plants of at least "
                f"{self.MIN_UTILITY_CAPACITY_MW:g} MW. Smaller plants are rooftop "
                "installations, which PowerPlantMatching only lists for Germany."
            )
        elif element.name == "photovoltaics_rooftop":
            data = self._get_rooftop(element)
            description = (
                "The existing capacity of rooftop photovoltaics is the total "
                "photovoltaic capacity of the IRENA Renewable Capacity Statistics "
                "minus the utility-scale capacity, i.e., the PowerPlantMatching "
                f"plants of at least {self.MIN_UTILITY_CAPACITY_MW:g} MW. Where the "
                "utility-scale capacity exceeds the IRENA total, the rooftop "
                "capacity is zero."
            )
        else:
            raise ValueError(
                f"No existing photovoltaic capacity is available for {element.name}."
            )
        source = SourceInformation(description=description, metadata=self.metadata)
        return element.capacity_existing.set_data(df=data, source=source, unit="GW")

    def _get_utility(self, element: Technology) -> pd.Series:
        """Utility-scale capacity (GW) per node and year of construction."""
        powerplantmatching = cast(PowerPlantMatching, self.data["powerplantmatching"])
        return powerplantmatching.calculate_capacity_existing(
            element,
            min_capacity=self.MIN_UTILITY_CAPACITY_MW,
            proxy_element_name="photovoltaics_utility",
        )

    def _get_rooftop(self, element: Technology) -> pd.Series:
        """Rooftop capacity (GW) per node and year of construction.

        The cumulative utility-scale capacity is subtracted from the cumulative
        IRENA capacity, and the difference is divided into yearly additions like
        the IRENA capacity itself.
        """
        reference_year = element.settings.time.reference_year
        total = cast(IRENASolarCapacity, self.data["irena"]).data
        total = total.loc[:, total.columns < reference_year]
        utility = self._get_utility(element).unstack("year_construction")
        years = range(min(utility.columns.min(), total.columns.min()), reference_year)
        utility = utility.reindex(columns=years).fillna(0).cumsum(axis=1)
        utility = utility.reindex(index=total.index, columns=total.columns).fillna(0)
        rooftop = (total - utility).clip(lower=0)

        addition = calculate_capacity_addition_from_cumulative(rooftop, element)
        data = cast(pd.Series, addition.stack())
        data = data[data != 0]
        return format_capacity_existing(data)
