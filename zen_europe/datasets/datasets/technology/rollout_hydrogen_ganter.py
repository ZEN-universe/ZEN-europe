from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import convert_country_names


class HydrogenRolloutGanter(Dataset[pd.Series]):
    """
    Dataset class for the near-term infrastructure rollout and investment strategies
    for net-zero hydrogen supply chains, based on the work of Alissa Ganter et al.
    (2024).

    """

    name = "hydrogen_rollout_ganter"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Near-term infrastructure rollout and investment strategies for "
                "net-zero hydrogen supply chains"
            ),
            author=["Alissa Ganter", "Paolo Gabrielli", "Giovanni Sansavini"],
            publication="Renewable and Sustainable Energy Reviews",
            publication_year=2024,
            url="https://www.sciencedirect.com/science/article/pii/S1364032124000376",
            doi="https://doi.org/10.1016/j.rser.2024.114314",
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
    def get_conversion_factor_SMR(self) -> list[dict[str, dict[str, Any]]]:
        """Get the conversion factor for SMR technologies.

        The data is obtained from the Supplementary Information, Table S2, p. 8.

        Returns:
            The conversion factor per input carrier.
        """
        conversion_factor = [
            {
                "natural_gas": {"default_value": 1 / 0.77, "unit": "GW/GW"},
                "electricity": {"default_value": 0.041, "unit": "GW/GW"},
            }
        ]
        return conversion_factor

    def get_capacity_existing_SMR(self) -> pd.Series:
        """
        Get the existing capacity for SMR technologies.
        We assume that all current ammonia plants and refineries use H2 from SMR.

        Returns:
            pd.Series: A pandas Series containing the existing capacity data.
        """
        path_capa_ex = self.path / "03-technology" / "capacity_existing" / "SMR"
        refineries = pd.read_excel(path_capa_ex / "Refinery_plants_OV.xlsx")
        ammonia_plants = pd.read_excel(path_capa_ex / "Ammonia_plants_OV.xlsx")
        refineries["Country"] = convert_country_names(refineries["Country"])
        ammonia_plants["Country"] = convert_country_names(ammonia_plants["Country"])
        capacity_existing_ref = (
            refineries.set_index("Country").groupby("Country").sum()
        )["H2 capacity (kg/h)"]
        capacity_existing_amm = (
            ammonia_plants.set_index("Country").groupby("Country").sum()
        )["Capacity (kg/h)"]
        # sum capacities
        capacity_existing = capacity_existing_ref.add(
            capacity_existing_amm, fill_value=0
        )
        capacity_existing = capacity_existing * Constants.HYDROGEN_KWH_PER_KG / 1e6
        return capacity_existing
