from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings


class JRCHydroPowerDatabase(Dataset[pd.DataFrame]):
    """
    JRC Hydro Power Database dataset class.

    """

    name = "jrc_hydro_power_database"

    TECHNOLOGY_MAPPING = {
        "HROR": "run-of-river_hydro",
        "HDAM": "reservoir_hydro",
        "HPHS": "pumped_hydro_storage",
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("JRC Hydro-power plants database"),
            author=[
                "Matteo De Felice",
                "Konstantinos Kanellopoulos",
                "Ignacio Hidalgo-Gonzaléz",
            ],
            publication="JRC",
            publication_year=2019,
            url="https://github.com/energy-modelling-toolkit/hydro-power-database/",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "capacity_existing"

    def _set_data(self) -> pd.DataFrame:
        if (
            get_active_cache_settings().overwrite_jrc_hydro_power_database
            or not (self.path / "jrc_hydro_power_database_data.feather").exists()
        ):
            url = "https://github.com/energy-modelling-toolkit/hydro-power-database/blob/master/data/jrc-hydro-power-plant-database.csv?raw=true"
            data = pd.read_csv(url)
            data.to_feather(self.path / "jrc_hydro_power_database_data.feather")
        else:
            data = pd.read_feather(self.path / "jrc_hydro_power_database_data.feather")
        data["type"] = data["type"].map(self.TECHNOLOGY_MAPPING)
        data = data[data["type"].isin(self.TECHNOLOGY_MAPPING.values())]
        data_agg = data.groupby(["type", "country_code"])[
            ["installed_capacity_MW", "storage_capacity_MWh"]
        ].sum()
        data_agg = data_agg.rename(
            index={"country_code": "node", "type": "technology"},
            columns={
                "installed_capacity_MW": "capacity_existing",
                "storage_capacity_MWh": "capacity_existing_storage",
            },
        )

        return data_agg / 1000

    # -------- methods ------------------------
    def get_capacity_existing(self, element, storage_capacity=False) -> pd.Series:
        """
        Get the existing capacity for a technology.

        Args:
            element: The element for which to get the existing capacity.
            storage_capacity: Whether to return storage capacity data.

        Returns:
            pd.Series: A pandas Series containing the existing capacity data.
        """
        assert element.name in self.data.index.get_level_values(0), (
            f"Existing capacity data for {element.name} is not available in the JRC "
            "Hydro-power plants database."
        )
        data = self.data.loc[element.name]
        if storage_capacity:
            data = data["capacity_existing_storage"]
        else:
            data = data["capacity_existing"]
        return data
