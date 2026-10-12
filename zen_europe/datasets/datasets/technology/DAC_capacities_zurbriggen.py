from __future__ import annotations

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

    def _set_data(self) -> pd.DataFrame:
        """
        The data is extracted from the GitHub repository of the Zurbriggen et al. paper.

        We allocate all icelandic storage projects to Norway,
        as we don't have a separate country in the model for Iceland.
        """
        data = pd.read_excel(self.path, sheet_name="All Projects", skiprows=1)
        data = data.rename(columns={"Unnamed: 7": "Technology Comments"})
        data = data.iloc[2:]
        data = data[
            data["Status"].isin(
                [
                    "Operational",
                    "Under Construction ",
                    "Design and Engineering Phase",
                    "FID",
                ]
            )
        ]
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
