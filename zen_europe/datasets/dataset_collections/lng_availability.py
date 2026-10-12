from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Carrier, Dataset

import numpy as np
from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.carrier.entsog import ENTSOG
from zen_europe.datasets.datasets.carrier.import_increase_gas import ImportIncreaseGas
from zen_europe.datasets.datasets.technology.gie_lng_map import GIELNGMap
from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import interpolate_missing_years, link_lng_countries


class LNGAvailability(DatasetCollection):
    """Extracting LNG availability data."""

    name = "lng_availability"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "gie_lng_map": GIELNGMap(self.source_path),
            "entsog": ENTSOG(self.source_path),
            "import_increase_gas": ImportIncreaseGas(self.source_path),
        }

    def get_availability_import(self, element: Carrier) -> Attribute:
        """
        Get the import availability for LNG.

        This function retrieves the LNG import availability data for the specified
        element.
        """
        gie_lng_map = cast(GIELNGMap, self.data["gie_lng_map"])
        lng_terminals = gie_lng_map._calculate_capacity_existing_lng(element=element)
        entsog = cast(ENTSOG, self.data["entsog"])
        entsog_data = entsog.get_availability_natural_gas()
        lng_areas = link_lng_countries()["lng"]
        availability = entsog_data.loc[lng_areas].sum(axis=0)
        availability = availability.droplevel(0)
        availability.index = availability.index.astype(int)
        availability = interpolate_missing_years(availability)
        import_increase_gas = cast(ImportIncreaseGas, self.data["import_increase_gas"])
        import_increase = (
            import_increase_gas.get_import_increase(region="lng")
            * 1000
            / entsog._TWh2bcm
        )  # convert to GWh
        availability = availability + import_increase

        fraction_lng = (
            lng_terminals.groupby(level=0).sum(numeric_only=True) / lng_terminals.sum()
        )
        lng_availability = pd.DataFrame(
            np.outer(fraction_lng, availability),
            index=fraction_lng.index,
            columns=availability.index,
            dtype=float,
        )

        opti_years = element.settings.time.years
        lng_availability = lng_availability.reindex(
            columns=opti_years, fill_value=np.nan
        )
        lng_availability = lng_availability.ffill(axis=1).bfill(axis=1)
        lng_availability.columns.names = ["year"]
        lng_availability.index.names = ["node"]
        lng_availability = lng_availability

        lng_availability_hourly = (
            lng_availability[element.settings.time.reference_year]
            / Constants.HOURS_PER_YEAR
        )
        lng_availability_hourly.name = "availability_import"
        lng_availability_hourly.index.name = "node"
        lng_availability_yearly = (
            lng_availability.sum()
            / lng_availability.sum()[element.settings.time.reference_year]
        )
        lng_availability_yearly.name = "availability_import_yearly_variation"
        lng_availability_yearly.index.name = "year"

        source = SourceInformation(
            description=(
                "LNG import availability data is derived from multiple sources. "
                "The main source is the ENTSOG dataset. We use the SciGRID dataset to "
                "determine the existing capacity of LNG terminals and "
                "thereby distribute the availability. "
            ),
            metadata=self.metadata,
        )
        return element.availability_import.set_data(
            source=source,
            df=lng_availability_hourly,
            yearly_variations_df=lng_availability_yearly,
            unit="GW",
        )
