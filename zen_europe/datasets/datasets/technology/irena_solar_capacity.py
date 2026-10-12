from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    convert_country_names,
    format_capacity_existing,
)


class IRENASolarCapacity(Dataset[pd.Series]):
    """
    IRENA solar capacity dataset class.

    """

    name = "irena_solar_capacity"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Renewable capacity statistics 2026"),
            author=["IRENA"],
            publication="IRENA",
            publication_year=2026,
            url="https://www.irena.org/Publications/2026/Mar/Renewable-capacity-statistics-2026",
            note=(
                "The values from 2006-2025 are from the Renewable Energy Statistics "
                "2016 report"
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "capacity_existing"

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path / "IRENA_solar_pv_capacity_MW_2006-2025.csv")
        data["Country"] = convert_country_names(data["Country"])
        data = data[data["Country"].notna()]
        data = data.set_index("Country")
        data = data.fillna(0)
        data.columns = data.columns.astype(int)
        return data / 1000

    # -------- methods ------------------------
    def get_capacity_existing(self, element) -> Attribute:
        """
        Get the existing capacity for a technology.

        Args:
            element: The element for which to get the existing capacity.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        assert element.name == "photovoltaics", (
            f"Existing capacity data for {element.name} is not available in the "
            "IRENASolarCapacity dataset."
        )
        data_add = calculate_capacity_addition_from_cumulative(self.data, element)
        data_add = data_add.stack().rename("capacity_existing")
        data_add.index.names = ["node", "year"]
        data_add = data_add[data_add != 0]
        reference_year = element.settings.time.reference_year
        data_add = data_add[data_add.index.get_level_values("year") < reference_year]
        data_add = format_capacity_existing(data_add)
        source = SourceInformation(
            description=(
                "The existing capacity data for photovoltaics is derived from the"
                " IRENA Renewable Capacity Statistics report. The reason why we do not"
                " use the PowerPlantMatching dataset for photovoltaics is"
                " that it only tracks utility-scale plants, not rooftop installations"
            ),
            metadata=self.metadata,
        )
        return element.capacity_existing.set_data(
            source=source,
            df=data_add,
            unit="GW",
        )
