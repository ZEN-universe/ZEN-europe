from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path
from typing import ClassVar, cast

import pandas as pd
import requests
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

from zen_europe.utils.time_series import (
    canonicalize_hourly_year,
    require_acceptable_year,
)


class When2Heat(Dataset[dict[str, pd.DataFrame]]):
    """Official When2Heat profiles and heat-pump coefficients of performance."""

    name = "when2heat"
    ACCEPTABLE_YEARS: ClassVar[tuple[int, ...]] = tuple(range(2008, 2023))
    VERSION = "2023-07-27"
    DOWNLOAD_URL = (
        "https://data.open-power-system-data.org/when2heat/" f"{VERSION}/when2heat.csv"
    )
    SOURCE_FILENAME = f"when2heat_{VERSION}.csv"

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="When2Heat",
            author=[
                "Oliver Ruhnau",
                "Lion Hirth",
                "Aaron Praktiknjo",
                "Jarusch Muessel",
            ],
            publication="Open power system data",
            publication_year=2023,
            url=f"https://data.open-power-system-data.org/when2heat/{self.VERSION}/",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        path = self.source_path / "02-carrier" / "heat" / "when2heat"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _set_data(self) -> dict[str, pd.DataFrame]:
        year = self.settings.time.resolved_weather_year
        require_acceptable_year(
            dataset_name=self.name,
            setting_name="weather_year",
            year=year,
            acceptable_years=self.ACCEPTABLE_YEARS,
        )
        data = self._load_year(year)
        timestamps = pd.DatetimeIndex(
            pd.to_datetime(data.pop("utc_timestamp"), utc=True)
        )
        data.index = timestamps

        cop_columns = data.columns.str.contains("_COP_ASHP_")
        profiles = canonicalize_hourly_year(
            data.loc[:, ~cop_columns],
            year=year,
            dataset_name=self.name,
            preserve_column_totals=True,
        )
        cop = canonicalize_hourly_year(
            data.loc[:, cop_columns], year=year, dataset_name=self.name
        )
        return {
            "profile": self._format_profiles(profiles),
            "COP": self._format_cop(cop),
        }

    def _load_year(self, year: int) -> pd.DataFrame:
        cache_path = self.path / f"when2heat_{self.VERSION}_{year}.feather"
        overwrite = self.settings.cache.overwrite_when2heat
        if cache_path.exists() and not overwrite:
            return pd.read_feather(cache_path)

        source_path = self.path / self.SOURCE_FILENAME
        if overwrite or not source_path.exists():
            self._download_source(source_path)

        delimiter = self._detect_delimiter(source_path)
        required = self._required_columns(source_path, delimiter)
        chunks: list[pd.DataFrame] = []
        for chunk in pd.read_csv(
            source_path,
            sep=delimiter,
            decimal="," if delimiter == ";" else ".",
            usecols=required,
            chunksize=100_000,
        ):
            timestamps = pd.to_datetime(chunk["utc_timestamp"], utc=True)
            selected = chunk.loc[timestamps.dt.year == year]
            if not selected.empty:
                chunks.append(selected)
        if not chunks:
            raise ValueError(f"{self.name}: source contains no rows for {year}.")
        data = pd.concat(chunks, ignore_index=True)
        data = self._fill_dst_gap(data, year)
        self._validate_timestamps(data["utc_timestamp"], year)
        self._write_feather_atomic(data, cache_path)
        return data

    def _fill_dst_gap(self, data: pd.DataFrame, year: int) -> pd.DataFrame:
        """Interpolate the known missing hour at the end of daylight saving."""
        timestamps = pd.DatetimeIndex(pd.to_datetime(data["utc_timestamp"], utc=True))
        expected = pd.date_range(
            start=pd.Timestamp(year=year, month=1, day=1, tz="UTC"),
            end=pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC"),
            freq="1h",
            inclusive="left",
        )
        missing = expected.difference(timestamps)
        unexpected = timestamps.difference(expected)
        is_dst_gap = (
            not timestamps.has_duplicates
            and len(missing) == 1
            and not len(unexpected)
            and missing[0].month == 10
            and missing[0].day >= 25
            and missing[0].dayofweek == 6
            and missing[0].hour == 1
        )
        if not is_dst_gap:
            return data

        values = data.drop(columns="utc_timestamp").copy()
        values.index = timestamps
        values = values.reindex(expected)
        gap = missing[0]
        values.loc[gap] = (
            values.loc[gap - pd.Timedelta(hours=1)]
            + values.loc[gap + pd.Timedelta(hours=1)]
        ) / 2
        values.insert(0, "utc_timestamp", expected)
        return values.reset_index(drop=True)

    @staticmethod
    def _detect_delimiter(source_path: Path) -> str:
        """Detect whether a When2Heat source uses commas or semicolons."""
        with source_path.open(encoding="utf-8-sig", newline="") as stream:
            header = stream.readline()

        try:
            return csv.Sniffer().sniff(header, delimiters=",;").delimiter
        except csv.Error as error:
            raise ValueError(
                f"Could not detect the delimiter of When2Heat source "
                f"'{source_path}'. Expected a comma- or semicolon-delimited file."
            ) from error

    def _required_columns(self, source_path: Path, delimiter: str) -> list[str]:
        header = pd.read_csv(source_path, sep=delimiter, nrows=0).columns
        required = [
            column
            for column in header
            if column == "utc_timestamp"
            or "_COP_ASHP_" in column
            or "_heat_profile_" in column
        ]
        has_cop = any("_COP_ASHP_" in column for column in required)
        has_profile = any("_heat_profile_" in column for column in required)
        if "utc_timestamp" not in required or not has_cop or not has_profile:
            raise ValueError(
                f"{self.name}: source does not contain the expected timestamp, "
                "heat-profile, and COP columns."
            )
        return required

    def _download_source(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f"{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(fd)
        temporary_path = Path(temporary_name)
        try:
            with requests.get(self.DOWNLOAD_URL, stream=True, timeout=120) as response:
                response.raise_for_status()
                with temporary_path.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            stream.write(chunk)
            self._validate_source(temporary_path)
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _validate_source(self, path: Path) -> None:
        delimiter = self._detect_delimiter(path)
        self._required_columns(path, delimiter)
        timestamp_column = pd.read_csv(path, sep=delimiter, usecols=["utc_timestamp"])[
            "utc_timestamp"
        ]
        timestamps = pd.to_datetime(timestamp_column, utc=True)
        present = set(timestamps.dt.year)
        missing = set(self.ACCEPTABLE_YEARS).difference(present)
        if missing:
            raise ValueError(
                f"{self.name}: downloaded source is missing years {sorted(missing)}."
            )
        for year in self.ACCEPTABLE_YEARS:
            year_timestamps = timestamp_column[timestamps.dt.year == year]
            validation_data = pd.DataFrame(
                {"utc_timestamp": year_timestamps, "value": 0.0}
            )
            repaired = self._fill_dst_gap(validation_data, year)
            self._validate_timestamps(repaired["utc_timestamp"], year)

    def _validate_timestamps(self, timestamps: pd.Series, year: int) -> None:
        index = pd.DatetimeIndex(pd.to_datetime(timestamps, utc=True))
        canonicalize_hourly_year(
            pd.DataFrame(index=index, data={"value": 0.0}),
            year=year,
            dataset_name=self.name,
        )

    @staticmethod
    def _write_feather_atomic(data: pd.DataFrame, destination: Path) -> None:
        temporary = destination.with_name(f"{destination.name}.{os.getpid()}.tmp")
        try:
            data.to_feather(temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _format_profiles(data: pd.DataFrame) -> pd.DataFrame:
        columns = data.columns.map(
            lambda x: (x.split("_")[0], x.split("_")[3], x.split("_")[4])
        )
        data.columns = pd.MultiIndex.from_tuples(
            columns, names=["node", "category", "house_type"]
        )
        house_type = data.columns.get_level_values("house_type")
        is_residential = house_type.isin(["MFH", "SFH"])
        residential = (
            data.loc[:, is_residential].T.groupby(level=["node", "category"]).mean().T
        )
        residential_columns = cast(list[tuple[str, str]], residential.columns.to_list())
        residential.columns = pd.MultiIndex.from_tuples(
            [(node, category, "RES") for node, category in residential_columns],
            names=["node", "category", "house_type"],
        )
        data = pd.concat([data.loc[:, ~is_residential], residential], axis=1)
        data = data.sort_index(axis=1).swaplevel(1, 2, axis=1).sort_index(axis=1)
        return data.rename(columns={"GB": "UK", "GR": "EL"}, level="node")

    @staticmethod
    def _format_cop(data: pd.DataFrame) -> pd.DataFrame:
        columns = data.columns.map(lambda x: (x.split("_")[0], x.split("_")[3]))
        data.columns = pd.MultiIndex.from_tuples(columns, names=["node", "category"])
        return data.rename(columns={"GB": "UK", "GR": "EL"}, level="node")

    def get_profiles(self) -> pd.DataFrame:
        """Return normalized heat-demand profiles."""
        return self.data["profile"]

    def get_COP(self) -> pd.DataFrame:
        """Return air-source heat-pump coefficients of performance."""
        return self.data["COP"]
