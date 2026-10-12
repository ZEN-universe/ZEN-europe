from __future__ import annotations

from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import pytz
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants


class TruckStandardLoadProfiles(Dataset[pd.Series]):
    """
    Truck standard load profiles dataset class.

    This class implements the specific behavior for the Truck Standard Load Profiles
    dataset.
    """

    name = "truck_standard_load_profiles"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Heavy-duty truck electrification and the impacts of "
                "depot charging on electricity distribution systems"
            ),
            author=[
                "Brennan Borlaug",
                "Matteo Muratori",
                "Madeline Gilleran",
                "David Woody",
                "William Muston",
                "Thomas Canada",
                "Andrew Ingram",
                "Hal Gresham",
                "Charlie McQueen",
            ],
            publication="Nature Energy",
            publication_year=2021,
            url="https://www.nature.com/articles/s41560-021-00855-0",
            doi="10.1038/s41560-021-00855-0",
            note="Supplementary Figure 8, 100 EVs, Constant min. power",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "02-carrier" / "transport" / "slp_HDT.xlsx"

    def _set_data(self) -> pd.Series:
        sheet = pd.read_excel(self.path, sheet_name="Sheet1").set_index("hour")
        profile = cast(pd.Series, sheet.squeeze())
        data = pd.concat([profile] * 365).reset_index(drop=True)
        data.index.name = "time"
        data = data / data.sum(axis=0)
        return data

    # -------- methods ------------------------
    def get_standard_load_profiles(self) -> pd.Series:
        """
        Get the standard load profiles.

        The urban, suburban, and rural load profiles are
        weighted by the share of the population in each region type.

        Returns:
            A pandas Series containing the standard load profile.
        """
        return self.data

    def shift_by_timezone(self, slp: pd.DataFrame) -> pd.DataFrame:
        """
        Shift the standard load profiles by the timezone of each country.

        Returns:
            A pandas DataFrame containing the shifted standard load profiles.
        """
        new_cols = slp.rename(columns={"EL": "GR", "UK": "GB"})
        tz = {
            old_cc: pytz.timezone(pytz.country_timezones[new_cc][0])
            for old_cc, new_cc in zip(slp.columns, new_cols.columns, strict=True)
            if new_cc in pytz.country_timezones
        }
        default_tz = tz["DE"]
        date = "2020-01-01"
        delta_t = {
            cc: (
                tz_cc.localize(pd.Timestamp(date))
                - default_tz.localize(pd.Timestamp(date))
            ).total_seconds()
            / Constants.SECONDS_PER_HOUR
            for cc, tz_cc in tz.items()
        }
        delta_t = {cc: val - 24 if val > 12 else val for cc, val in delta_t.items()}
        slp_shifted = slp.apply(
            lambda col: pd.Series(
                np.roll(col, int(delta_t[col.name])), index=col.index
            ),
            axis=0,
        )
        return slp_shifted
