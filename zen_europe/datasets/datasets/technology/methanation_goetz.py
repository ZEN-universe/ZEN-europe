from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation


class MethanationGoetz(Dataset[pd.DataFrame]):
    """
    Dataset class for the techno-economic analysis of methanation processes,
    based on the work of Manuel Götz et al. (2016).

    """

    name = "methanation_goetz"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Renewable Power-to-Gas: A technological and economic review"),
            author=[
                "Manuel Götz",
                "Jonathan Lefebvre",
                "Friedemann Mörs",
                "Amy McDaniel Koch",
                "Frank Graf",
                "Siegfried Bajohr",
                "Rainer Reimert",
                "Thomas Kolb",
            ],
            publication="Renewable Energy",
            publication_year=2016,
            url="https://www.sciencedirect.com/science/article/pii/S0960148115301610",
            doi="https://doi.org/10.1016/j.renene.2015.07.066",
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
    def get_conversion_factor_methanation(
        self, element: ConversionTechnology
    ) -> dict[str, dict[str, float]]:
        """
        Get the conversion factor for methanation technologies.

        Returns:
            pd.Series: A pandas Series containing the conversion factor data.
        """
        attr = element.conversion_factor
        efficiency = 0.78
        produced_methane = 332  # MW
        consumed_carbon = 30000 * 1.836 / 1000  # m3/h -> tCO2/h
        cf = [
            {"hydrogen": {"default_value": 1 / efficiency, "unit": "GWh/GWh"}},
            {
                "carbon": {
                    "default_value": consumed_carbon / produced_methane,
                    "unit": "ktCO2/GWh",
                }
            },
        ]
        source = SourceInformation(
            description=(
                "The conversion factor of methanation is derived "
                "from Götz et al. (2016), 'Renewable Power-to-Gas: "
                "A technological and economic review', Renewable Energy"
            ),
            metadata=self.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr
