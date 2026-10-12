from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import convert_country_names


class GlobalCCSInstitute(Dataset[pd.DataFrame]):
    """
    Dataset class for the near-term infrastructure rollout and investment strategies
    for net-zero hydrogen supply chains, based on the work of Alissa Ganter et al.
    (2024).

    """

    name = "global_ccs_institute"

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

    def _set_data(self) -> dict[str, pd.Series]:
        """
        No data to be set.
        """
        data = {}

        data = pd.Series(data)
        return data

    # -------- methods ------------------------
    def get_conversion_factor_SMR(self) -> dict[str, dict[str, float]]:
        """Get the conversion factor for SMR technologies.

        The data is obtained from the Supplementary Information, Table S2, p. 8.

        Returns:
            pd.Series: A pandas Series containing the conversion factor data.
        """
        conversion_factor = [
            {
                "natural_gas": {"default_value": 1 / 0.77, "unit": "GW/GW"},
                "electricity": {"default_value": 0.041, "unit": "GW/GW"},
            }
        ]
        return conversion_factor

    def get_capacity_existing_SMR(self) -> dict[str, dict[str, float]]:
        """
        Get the existing capacity for SMR technologies.
        We assume that all current ammonia plants and refineries use H2 from SMR.

        Returns:
            pd.Series: A pandas Series containing the existing capacity data.
        """
        path_capa_ex = self.source_path / "03-technology" / "capacity_existing" / "SMR"
        capacity_existing_ref = pd.read_excel(path_capa_ex / "Refinery_plants_OV.xlsx")
        capacity_existing_amm = pd.read_excel(path_capa_ex / "Ammonia_plants_OV.xlsx")
        capacity_existing_ref["Country"] = convert_country_names(
            capacity_existing_ref["Country"]
        )
        capacity_existing_amm["Country"] = convert_country_names(
            capacity_existing_amm["Country"]
        )
        capacity_existing_ref = (
            capacity_existing_ref.set_index("Country").groupby("Country").sum()
        )
        capacity_existing_amm = (
            capacity_existing_amm.set_index("Country").groupby("Country").sum()
        )
        capacity_existing_ref = capacity_existing_ref["H2 capacity (kg/h)"]
        capacity_existing_amm = capacity_existing_amm["Capacity (kg/h)"]
        # sum capacities
        capacity_existing = capacity_existing_ref.add(
            capacity_existing_amm, fill_value=0
        )
        capacity_existing = capacity_existing * Constants.HYDROGEN_KWH_PER_KG / 1e6
        return capacity_existing
