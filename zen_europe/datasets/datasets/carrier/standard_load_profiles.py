from __future__ import annotations

from pathlib import Path
from typing import ClassVar, cast

import numpy as np
import pandas as pd
import pytz
from zen_creator import Element
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

from zen_europe.utils.constants import Constants
from zen_europe.utils.time_series import require_acceptable_year

_REGION_TYPES = {"urban": "HT1", "suburban": "HT3", "rural": "HT6"}
_DAY_TYPES = {"w": "Werktag", "we": "Wochenende"}
_COL_NAME = "Zuhause, am Arbeitsplatz und an öffentlichen Orten laden"


class StandardLoadProfiles(Dataset[dict[str, pd.DataFrame]]):
    """
    Standard load profiles dataset class.

    This class implements the specific behavior for the Standard Load Profiles dataset.
    """

    name = "standard_load_profiles"
    ACCEPTABLE_YEARS: ClassVar[tuple[int, ...]] = (2019, 2020)

    def __init__(
        self, settings: Settings, source_path: Path | str | None = None
    ) -> None:
        self.settings = settings
        require_acceptable_year(
            settings.time.time_series_year,
            dataset_name=self.name,
            setting_name="time_series_year",
            acceptable_years=self.ACCEPTABLE_YEARS,
        )
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Erstellung und Auswertung repräsentativer Mobilitäts- "
                "und Ladeprofile für Elektrofahrzeuge in Deutschland"
            ),
            author=["Daniel Heinz"],
            publication=(
                "Institut für Industriebetriebslehre und Industrielle Produktion"
            ),
            publication_year=2018,
            url="https://publikationen.bibliothek.kit.edu/1000086372",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path)
            / "02-carrier"
            / "transport"
            / "Standardlastprofile_Elektrofahrzeuge.xlsx"
        )

    def _set_data(self) -> dict[str, pd.DataFrame]:
        data: dict[str, pd.DataFrame] = {}
        for day_type, day_code in _DAY_TYPES.items():
            data_reg: dict[str, pd.Series] = {}
            for region_type, region_code in _REGION_TYPES.items():
                sheet_name = f"{region_code}_{day_code}"
                df = pd.read_excel(
                    self.path, sheet_name=sheet_name, header=2
                ).set_index("Ladeszenario")
                df = df.iloc[:, np.where(df.columns == _COL_NAME)[0][0] :]
                df.columns = cast(pd.Series, df.loc["Ladeorte"])
                df = df.iloc[2:]
                # average per hour
                df.index = pd.to_datetime(df.index)
                df = df.resample("1h").mean().iloc[:-1]
                # sum over location (home, work, public)
                data_reg[region_type] = df.sum(axis=1)
            data[day_type] = pd.concat(data_reg, keys=data_reg.keys(), axis=1)
        return data

    # -------- methods ------------------------
    def get_standard_load_profiles(
        self, share_regions: pd.DataFrame, element: Element
    ) -> pd.DataFrame:
        """
        Get the standard load profiles.

        The urban, suburban, and rural load profiles are
        weighted by the share of the population in each region type.

        Returns:
            A pandas DataFrame containing the standard load profiles.
        """
        data = {}
        for day_type in _DAY_TYPES:
            data_d = self.data[day_type]
            data[day_type] = data_d.dot(share_regions)
        time_series_year = element.settings.time.time_series_year
        require_acceptable_year(
            time_series_year,
            dataset_name=self.name,
            setting_name="time_series_year",
            acceptable_years=self.ACCEPTABLE_YEARS,
        )
        days = pd.date_range(
            f"{time_series_year}-01-01", f"{time_series_year}-12-31", freq="1D"
        )
        days = days[~((days.month == 2) & (days.day == 29))]
        data_ts = pd.concat(
            [data["w" if day.weekday() < 5 else "we"] for day in days], axis=0
        )
        data_ts = data_ts.reset_index(drop=True)
        data_ts.index.name = "time"
        return data_ts

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
