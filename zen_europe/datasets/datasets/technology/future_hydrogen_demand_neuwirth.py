from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute

from zen_europe.utils.constants import Constants


class FutureHydrogenDemandNeuwirth(Dataset[pd.DataFrame]):
    """
    Dataset class for the future hydrogen demand projections from Neuwirth et al.
    (2021).

    """

    name = "future_hydrogen_demand_neuwirth"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "The future potential hydrogen demand in energy-intensive industries - "
                "a site-specific approach applied to Germany"
            ),
            author=["Marius Neuwirth", "Tobias Fleitner", "Pia Manz", "RenÃ© Hofmann"],
            publication="Energy Conversion and Management",
            publication_year=2021,
            url="https://www.sciencedirect.com/science/article/pii/S0196890421012280",
            doi="https://doi.org/10.1016/j.enconman.2021.115052",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> dict[str, pd.Series]:
        """
        No data to be set.
        """
        data = {}

        data = pd.Series(data)
        return data

    # -------- methods ------------------------
    def get_conversion_factor_refining(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the conversion factor for refining technologies.

        Returns:
            pd.Series: A pandas Series containing the conversion factor data.
        """
        hydrogen_demand = (
            0.514 * Constants.TOE_PER_MWH
        )  # between 0.389 - 0.639, Table 2
        conversion_factor = [
            {
                "crude_oil": {"default_value": 1, "unit": "GW/GW"},
                "hydrogen": {"default_value": hydrogen_demand, "unit": "GW/GW"},
            }
        ]
        attr = element.conversion_factor
        attr.set_data(
            default_value=conversion_factor,
            source=SourceInformation(
                description=(
                    "The conversion factor of refining is "
                    "assumed to be a lossless crude-oil-to-oil conversion and a "
                    "hydrogen demand of 0.514 MWh H2 per toe of oil product."
                ),
                metadata=self.metadata,
            ),
        )
        return attr
