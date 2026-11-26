from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class CerameUnie2021(Dataset[pd.Series]):
    """
    Dataset class for the Ceramic Roadmap to 2050 of Cerame-Unie, the European
    Ceramic Industry Association.
    """

    name = "cerame_unie2021"

    # share of the emission sources in the CO2 emissions of the European ceramic
    # industry in 2020, chapter "Continuing our Path towards Climate Neutrality",
    # p. 30; indirect emissions are mainly from electricity production
    EMISSION_SHARES = {"fuel_combustion": 0.64, "indirect": 0.19, "process": 0.17}

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Ceramic Roadmap to 2050: Continuing our Path towards Climate "
                "Neutrality"
            ),
            author=["Cerame-Unie, The European Ceramic Industry Association"],
            publication="Cerame-Unie",
            publication_year=2021,
            url="https://www.cerameunie.eu/media/zyqdwwwp/ceramic-roadmap-to-2050.pdf",
            note=(
                "Chapter 'Continuing our Path towards Climate Neutrality', also at "
                "https://www.ceramicroadmap2050.eu/chapters/"
                "continuing-our-path-towards-climate-neutrality/"
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        data: dict[str, float] = {}
        return pd.Series(data)

    # -------- methods ------------------------
    def get_emission_share(self, source: str) -> float:
        """
        Get the share of an emission source (fuel combustion, indirect, process) in
        the CO2 emissions of the European ceramic industry in 2020, p. 30.

        Returns:
            float: The share of the emission source.
        """
        if source not in self.EMISSION_SHARES:
            raise ValueError(f"Emission share of {source} is not defined.")
        return self.EMISSION_SHARES[source]

    def get_process_per_combustion_emissions(self) -> float:
        """
        Get the process CO2 per fuel combustion CO2 of the European ceramic industry
        in 2020, p. 30.

        Returns:
            float: The process emissions divided by the fuel combustion emissions.
        """
        return self.get_emission_share("process") / self.get_emission_share(
            "fuel_combustion"
        )
