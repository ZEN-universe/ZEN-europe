from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class IEANetZeroRoadmap(Dataset[pd.Series]):
    """
    Global direct air capture (DAC) in the IEA Net Zero Emissions by 2050
    scenario of the IEA Net Zero Roadmap (2023 update), CCUS chapter.

    The report states the CO2 captured by DAC per year. It is used as the
    cumulative global DAC capacity, which neglects the capacity factor (about
    10% more nameplate capacity at a capacity factor of 90%).
    """

    name = "iea_net_zero_roadmap"

    # CO2 captured by DAC worldwide [tCO2/yr]
    DAC_CAPTURE: dict[int, float] = {
        2030: 80e6,
        2035: 203e6,
        2050: 1041e6,
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Net Zero Roadmap:Carbon capture, utilisation and storage"),
            author=["International Energy Agency"],
            publication="International Energy Agency",
            publication_year=2023,
            url="https://www.iea.org/reports/CCUS",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        data = pd.Series(self.DAC_CAPTURE, name="capacity", dtype=float)
        data.index.name = "year"
        return data

    # -------- methods ------------------------
    def get_global_dac_capacity(self) -> pd.Series:
        """Global DAC capacity [tCO2/yr] in the reported years."""
        return self.data.copy()
