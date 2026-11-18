from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

logger = logging.getLogger(__name__)


class When2Heat(Dataset[dict[str, pd.DataFrame]]):
    """
    When2Heat dataset class.

    This class implements the specific behavior for the When2Heat dataset.
    """

    name = "when2heat"

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("When2Heat"),
            author=[
                "Oliver Ruhnau",
                "Lion Hirth",
                "Aaron Praktiknjo",
                "Jarusch Muessel",
            ],
            publication="Open power system data",
            publication_year=2023,
            url="https://data.open-power-system-data.org/when2heat/",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "heat" / "when2heat_filtered.csv"

    def _set_data(self) -> dict[str, pd.DataFrame]:
        data = pd.read_csv(self.path)
        time_series_year = self.settings.time.time_series_year
        years = pd.to_datetime(data["utc_timestamp"]).dt.year
        data_sel = data[years == time_series_year]
        ts = pd.to_datetime(data_sel["utc_timestamp"])
        hour_of_year = (ts.dt.dayofyear - 1) * 24 + ts.dt.hour
        data_sel.index = hour_of_year
        data_sel = data_sel.drop(columns=["utc_timestamp", "cet_cest_timestamp"])
        data_sel = data_sel.reindex(
            range(data_sel.index.min(), data_sel.index.max() + 1),
            method="ffill",
            axis=0,
        )
        country_idx = data_sel.columns.map(
            lambda x: (x.split("_")[0], "_".join(x.split("_")[1:]))
        )
        country_idx = pd.MultiIndex.from_tuples(country_idx, names=["node", "category"])
        is_COP = country_idx.get_level_values("category").str.contains("COP")
        data_COP = data_sel.loc[:, is_COP]
        data_profile = data_sel.loc[:, ~is_COP]
        split_category = data_profile.columns.map(
            lambda x: (x.split("_")[0], x.split("_")[3], x.split("_")[4])
        )
        data_profile.columns = pd.MultiIndex.from_tuples(
            split_category, names=["node", "category", "house_type"]
        )
        split_category_COP = data_COP.columns.map(
            lambda x: (x.split("_")[0], x.split("_")[3])
        )
        data_COP.columns = pd.MultiIndex.from_tuples(
            split_category_COP, names=["node", "category"]
        )

        # merge single-family and multi-family houses into one residential category,
        # assuming the same share
        house_type = data_profile.columns.get_level_values("house_type")
        is_res = house_type.isin(["MFH", "SFH"])
        res_profile = (
            data_profile.loc[:, is_res].T.groupby(level=["node", "category"]).mean().T
        )
        res_profile.columns = pd.MultiIndex.from_tuples(
            [(node, category, "RES") for node, category in res_profile.columns],
            names=["node", "category", "house_type"],
        )
        data_profile = pd.concat(
            [data_profile.loc[:, ~is_res], res_profile], axis=1
        ).sort_index(axis=1)
        data_profile = data_profile.swaplevel(1, 2, axis=1).sort_index(axis=1)
        # rename GB->UK and GR->EL on first level
        data_profile = data_profile.rename(
            columns={"GB": "UK", "GR": "EL"}, level="node"
        )
        data_COP = data_COP.rename(columns={"GB": "UK", "GR": "EL"}, level="node")

        return {"profile": data_profile, "COP": data_COP}

    # -------- methods ------------------------
    def get_profiles(self) -> pd.DataFrame:
        """
        Get the heat demand profiles.

        Args:
            element (Carrier): The carrier element for which to get the demand.

        Returns:
            A pandas DataFrame containing the demand data for the specified carrier.
        """
        return self.data["profile"]

    def get_COP(self) -> pd.DataFrame:
        """
        Get the COP data.

        Args:
            element (Carrier): The carrier element for which to get the COP data.

        Returns:
            A pandas DataFrame containing the COP data for the specified carrier.
        """
        return self.data["COP"]
