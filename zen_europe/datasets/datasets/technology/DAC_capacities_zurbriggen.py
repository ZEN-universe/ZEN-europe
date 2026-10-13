from __future__ import annotations

from functools import cached_property
from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import convert_ISO3_to_ISO2, format_capacity_existing


class DACCapacitiesZurbriggen(Dataset[pd.DataFrame]):
    """
    Dataset class for the existing DAC capacities based on the Zurbriggen Nature
    Communications Paper.

    """

    name = "DAC_capacities_zurbriggen"

    # Global DAC capacity [tCO2/yr] of the probabilistic diffusion model of the
    # paper: the mean initial capacity in 2030 (8.8 MtCO2/yr in the base case, ten
    # times more with a short-term policy push) and the median capacity in 2050
    # for the growth analogues.
    GLOBAL_CAPACITY_PATHWAYS: dict[str, dict[int, float]] = {
        "LNG analogue": {2030: 8.8e6, 2050: 20e6},
        "ammonia analogue": {2030: 8.8e6, 2050: 70e6},
        "ammonia + policy": {2030: 88e6, 2050: 600e6},
        "wind + policy": {2030: 88e6, 2050: 1600e6},
    }

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Short-term action is key for gigaton-scale Direct Air Capture by 2050"
            ),
            author=[
                "Tatjana Zurbriggen",
                "Nicoletta Brazzola",
                "Adrian Odenweller",
                "Falko Ueckerdt",
                "Joeri Rogelj",
            ],
            publication="Nature Communications",
            publication_year=2026,
            url="https://github.com/zztatjana/Feasibility-of-DAC-deployment-by-2050/blob/v1.0.2/01_input_data_new/Capacity%20DAC%20Projects%20Database%202024.xlsx",
            doi="https://doi.org/10.1038/s41467-026-72691-3",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path)
            / "03-technology"
            / "capacity_existing"
            / "DAC"
            / "Capacity DAC Projects Database 2024.xlsx"
        )

    @cached_property
    def _projects(self) -> pd.DataFrame:
        """All projects of the database, worldwide and of every status."""
        data = pd.read_excel(self.path, sheet_name="All Projects", skiprows=1)
        data = data.rename(columns={"Unnamed: 7": "Technology Comments"})
        return data.iloc[2:]

    def _set_data(self) -> pd.DataFrame:
        """
        The data is extracted from the GitHub repository of the Zurbriggen et al. paper.

        We allocate all icelandic storage projects to Norway,
        as we don't have a separate country in the model for Iceland.
        """
        data = self._projects
        data = data[
            data["Status"].isin(
                [
                    "Operational",
                    "Under Construction ",
                    "Design and Engineering Phase",
                    "FID",
                ]
            )
        ].copy()
        data["node"] = convert_ISO3_to_ISO2(data["Country"])
        data["node"] = data["node"].replace({"IS": "NO"})
        data = data[data["node"].notna()]
        data["year_construction"] = pd.to_numeric(data["Date online"], errors="coerce")
        data["Capacity"] = (
            data["Capacity"] / Constants.HOURS_PER_YEAR
        )  # from tCO2/year to tCO2/h
        data = data[data["Capacity"].notna()]

        return data

    # -------- methods ------------------------
    def get_global_dac_capacity_operational(self) -> pd.Series:
        """
        Cumulative global capacity [tCO2/yr] of the operational DAC projects, by
        the year they came online.

        Unlike `get_capacity_existing`, all countries are included and only
        projects with the status "Operational" are counted.
        """
        data = self._projects
        operational = data[data["Status"].astype(str).str.strip() == "Operational"]
        year = pd.to_numeric(operational["Date online"], errors="coerce")
        capacity = pd.to_numeric(operational["Capacity"], errors="coerce")
        cumulative = capacity.groupby(year).sum().cumsum()
        cumulative.index = cumulative.index.astype(int)
        cumulative.index.name = "year"
        cumulative.name = "capacity"
        return cumulative.astype(float)

    def get_global_dac_capacity(self, pathway: str) -> pd.Series:
        """
        Global DAC capacity [tCO2/yr] of `pathway` in the reported years.

        The pathways are one of `GLOBAL_CAPACITY_PATHWAYS`: base case or enhanced
        policy, with the growth of a historical analogue technology.
        """
        if pathway not in self.GLOBAL_CAPACITY_PATHWAYS:
            raise ValueError(
                f"Unknown DAC pathway '{pathway}' of Zurbriggen et al., expected one "
                f"of {list(self.GLOBAL_CAPACITY_PATHWAYS)}."
            )
        data = pd.Series(
            self.GLOBAL_CAPACITY_PATHWAYS[pathway], name="capacity", dtype=float
        )
        data.index.name = "year"
        return data

    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """
        Returns the existing DAC capacity from the Zurbriggen et al. paper.
        """
        attr = element.capacity_existing
        data = (
            self.data[["node", "year_construction", "Capacity"]]
            .groupby(["node", "year_construction"])["Capacity"]
            .sum()
        )
        if not self.settings.investment.set_future_CCS_investments:
            reference_year = self.settings.time.reference_year
            data = data[
                data.index.get_level_values("year_construction") <= reference_year - 1
            ]
        data = format_capacity_existing(data)
        return attr.set_data(
            df=data,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The existing DAC capacity is based on the Zurbriggen et al. paper "
                    "'Short-term action is key for gigaton-scale Direct Air Capture by "
                    "2050'."
                ),
                metadata=self.metadata,
            ),
        )
