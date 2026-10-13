from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import cast

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings
from zen_europe.utils.utils import convert_country_names


class GloHydroRes(Dataset[pd.Series]):
    """
    GloHydroRes Database dataset class.

    """

    name = "glohydrores"

    TECHNOLOGY_MAPPING = {
        "ROR": "run-of-river_hydro",
        "STO": "reservoir_hydro",
        "PS": "pumped_hydro_storage",
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Global dataset combining open-source hydropower plant and reservoir "
                "data"
            ),
            author=[
                "Jignesh Shah",
                "Jing Hu",
                "Oreane Y. Edelenbosch",
                "Michelle T. H. van Vliet",
            ],
            publication="Scientific Data",
            publication_year=2025,
            url="https://zenodo.org/records/14526360",
            doi="https://doi.org/10.1038/s41597-025-04975-0",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "capacity_existing"

    def _set_data(self) -> pd.Series:
        if get_active_cache_settings().overwrite_glohydrores or not (
            os.path.exists(self.path / "glohydrores_data.feather")
            and os.path.exists(self.path / "glohydrores_data_raw.feather")
        ):
            data = pd.read_excel(self.path / "GloHydroRes_vs1.xlsx", sheet_name="Data")
            logging.info(f"Before filtering: {len(data)} power plants")
            data["country_code"] = convert_country_names(data["country"])
            data = data[data["country_code"].notna()]
            logging.info(f"After selecting countries: {len(data)} power plants")
            data.loc[:, "technology"] = data["plant_type"].map(self.TECHNOLOGY_MAPPING)
            data = data[data["technology"].isin(self.TECHNOLOGY_MAPPING.values())]
            logging.info(f"After assigning technologies: {len(data)} power plants")
            data = data[data["year"].notna()]
            logging.info(f"After removing nan years: {len(data)} power plants")
            data_agg = data.groupby(["technology", "country_code", "year"])[
                "capacity_mw"
            ].sum()
            data_agg = data_agg.rename({"capacity_mw": "capacity_existing"})
            data_agg.index.names = ["technology", "node", "year"]
            data_agg.to_frame("capacity_existing").to_feather(
                self.path / "glohydrores_data.feather"
            )
            data.to_feather(self.path / "glohydrores_data_raw.feather")
        else:
            data_agg = cast(
                pd.Series,
                pd.read_feather(self.path / "glohydrores_data.feather").squeeze(),
            )

        return data_agg / 1000

    # -------- methods ------------------------
    def get_capacity_existing(self, element) -> pd.Series:
        """
        Get the existing capacity for a technology.

        Args:
            element: The element for which to get the existing capacity.

        Returns:
            pd.Series: A pandas Series containing the existing capacity data.
        """
        assert element.name in self.data.index.get_level_values(0), (
            f"Existing capacity data for {element.name} is not available in the JRC "
            "Hydro-power plants database."
        )
        data = self.data.loc[element.name]
        return data
