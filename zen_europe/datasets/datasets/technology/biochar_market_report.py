from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    convert_country_names,
    format_capacity_existing,
)


class BiocharMarketReport(Dataset[pd.DataFrame]):
    """
    Dataset class for the biochar market report.

    """

    name = "biochar_market_report"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("European Biochar Market Report 2025 2026"),
            author=["Biochar Europe"],
            publication="Biochar Europe",
            publication_year=2026,
            url="https://www.biochareurope.eu/resource/market-report-2025-2026",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.Series]:
        """
        Biochar production by regions/country, p. 46.

        The values for 2019 and 2020 are from the 2023 - 2024 report,
        while the values for 2021-2026 are from the 2025-2026 report.
        """
        biochar_capacity = {
            2019: {
                "Germany": 7000,
                "Austria and Switzerland": 2500,
                "Nordics": 2000,
                "other countries": 2500,
            },
            2020: {
                "Germany": 8500,
                "Austria and Switzerland": 2000,
                "Nordics": 5500,
                "other countries": 4500,
            },
            2021: {
                "Germany": 13000,
                "Austria and Switzerland": 4500,
                "Nordics": 9000,
                "other countries": 8500,
            },
            2022: {
                "Germany": 17000,
                "Austria and Switzerland": 9500,
                "Nordics": 13500,
                "other countries": 13000,
            },
            2023: {
                "Germany": 19500,
                "Austria and Switzerland": 12000,
                "Nordics": 21000,
                "other countries": 22500,
            },
            2024: {
                "Germany": 21500,
                "Austria and Switzerland": 12000,
                "Nordics": 25500,
                "other countries": 25000,
            },
            2025: {
                "Germany": 21500,
                "Austria and Switzerland": 14500,
                "Nordics": 27500,
                "other countries": 27500,
            },
            2026: {
                "Germany": 21500,
                "Austria and Switzerland": 20500,
                "Nordics": 30500,
                "other countries": 32500,
            },
        }
        # the relevant countries from p. 46, assume equal distribution of countries in
        # regions
        countries_nordics = ["Denmark", "Finland", "Sweden"]
        countries_austria_switzerland = ["Austria", "Switzerland"]
        countries_other = ["France", "Spain", "United Kingdom"]

        data = pd.DataFrame(biochar_capacity)
        for country in countries_nordics:
            data.loc[country, :] = data.loc["Nordics"] / len(countries_nordics)
        for country in countries_austria_switzerland:
            data.loc[country, :] = data.loc["Austria and Switzerland"] / len(
                countries_austria_switzerland
            )
        for country in countries_other:
            data.loc[country, :] = data.loc["other countries"] / len(countries_other)
        data = data.drop(["Nordics", "Austria and Switzerland", "other countries"])

        data.index = pd.Index(
            convert_country_names(data.index.to_series()).values, name="node"
        )

        return data

    # -------- methods ------------------------
    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """
        Returns the existing capacity from the biochar market report.

        The
        """
        attr = element.capacity_existing
        data = self.data
        data = calculate_capacity_addition_from_cumulative(data, element)
        data = data * Constants.BIOCHAR_GWH_PER_TON / 8760  # GW
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_pyrolysis()
        biochar_per_oil = next((item for item in cf if "hard_coal" in item), None)
        biochar_per_oil = biochar_per_oil["hard_coal"]["default_value"]

        capacity_existing = data / biochar_per_oil
        capacity_existing = capacity_existing.stack()
        capacity_existing = format_capacity_existing(capacity_existing)
        return attr.set_data(
            default_value=0,
            df=capacity_existing,
            unit="GW",
            source=SourceInformation(
                description=(
                    "The existing capacity of pyrolysis is extracted from the Biochar"
                    " Market Report, and distributed among the mentioned countries."
                    " The capacity is then converted to biooil output in GW."
                ),
                metadata=self.metadata,
            ),
        )
