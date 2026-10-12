from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.carriers.carrier import Carrier
import pandas as pd
from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute, SourceInformation

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    convert_country_names,
    format_capacity_existing,
    interpolate_missing_years,
)


class IFA(Dataset[pd.DataFrame]):
    """
    International Fertilizer Association dataset class.

    This class implements the specific behavior for the IFA dataset.
    """

    name = "ifa"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Ammonia demand from Gabrielli et al. (2023) and "
                "the International Fertilizer Association (IFA)"
            ),
            author=[
                "Paolo Gabrielli",
                "Lorenzo Rosa",
                "Matteo Gazzani",
                "Raoul Meys",
                "André Bardow",
                "Marco Mazzotti",
                "Giovanni Sansavini",
                "International Fertilizer Association",
            ],
            publication="One Earth",
            publication_year=2023,
            url="https://www.sciencedirect.com/science/article/pii/S2590332223002075",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "industry"

    def _set_data(self) -> dict[str, pd.DataFrame]:
        ys = [2020, 2050]
        data = {}
        for y in ys:
            df = pd.read_excel(
                self.path
                / f"Chemical Industry - Summary Calculations Geospatial {y}.xlsx",
                sheet_name="Sheet1",
            )
            data[str(y)] = df
        return data

    # -------- methods ------------------------
    def _prepare_data(self) -> pd.DataFrame:
        """
        Prepare the data for the given element.

        This method retrieves the data for the given element and prepares it for further
        processing.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the prepared data.
        """
        ds = {}
        for y, df in self.data.items():
            d = df[["Country", f"Ammonia production in {y} [1,000 tNH3]"]]
            d.loc[:, "Country"] = convert_country_names(d["Country"])
            d = d.dropna().set_index("Country").squeeze()
            ds[int(y)] = d
        d = pd.concat(ds, axis=1)
        d = interpolate_missing_years(d)
        d = d / Constants.HOURS_PER_YEAR * 1000 * Constants.AMMONIA_GWH_PER_TON
        d = d[(d != 0).all(axis=1)]

        d.index.name = "node"
        d = d.sort_index()
        return d

    def get_demand(self, element: Carrier) -> Attribute:
        """
        Get the demand of ammonia from the IFA dataset.

        This method retrieves the demand data for ammonia from the IFA dataset
        and returns it as an Attribute object.

        Args:
            element (Carrier): The carrier element for which to get the demand.
        """
        d = self._prepare_data()
        reference_year = element.settings.time.reference_year
        yearly_variation = d.div(d[reference_year], axis=0)
        reference_year_values = d[reference_year]
        reference_year_values.name = "demand"

        source = SourceInformation(
            description=(
                "Ammonia demand from Gabrielli et al. (2023) and the "
                "International Fertilizer Association (IFA). The data was first"
                " produced by IFA and then processed by Gabrielli et al. (2023)."
                " Converted from 1000 tNH3 to GW (assume constant demand) and "
                "interpolated to fill missing years; the yearly variation is expressed "
                "relative to the reference year."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=reference_year_values,
            yearly_variations_df=yearly_variation,
            unit="GW",
        )

    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """
        Get the existing capacity for haber bosch from the IFA dataset.

        This method retrieves the existing capacity data for ammonia from the IFA
        dataset
        and returns it as an Attribute object.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the existing capacity.
        """
        d = self._prepare_data()
        reference_year = element.settings.time.reference_year
        d = d[reference_year].to_frame(name=reference_year - 1)
        capacity_existing = calculate_capacity_addition_from_cumulative(d, element)
        capacity_existing = format_capacity_existing(capacity_existing)
        source = SourceInformation(
            description=(
                "Existing ammonia production capacity derived from the IFA dataset. "
                "The data was first produced by IFA and then processed by Gabrielli et "
                "al. (2023)."
            ),
            metadata=self.metadata,
        )
        return element.capacity_existing.set_data(
            source=source,
            df=capacity_existing,
            unit="GW",
        )
