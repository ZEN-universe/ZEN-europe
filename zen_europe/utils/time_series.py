"""Shared year selection and hourly-calendar validation utilities."""

from __future__ import annotations

import calendar
from collections.abc import Collection
from typing import cast, overload

import pandas as pd

DataFrameOrSeries = pd.DataFrame | pd.Series

MODEL_HOURS_PER_YEAR = 8760
DEMAND_TIME_SERIES_YEARS = (2019, 2020)
WEATHER_YEARS = tuple(range(2008, 2023))


def require_acceptable_year(
    year: int,
    *,
    dataset_name: str,
    setting_name: str,
    acceptable_years: Collection[int],
) -> int:
    """Validate a requested year against a dataset's supported years.

    Args:
        year: Requested calendar year.
        dataset_name: Human-readable dataset identifier used in errors.
        setting_name: Setting that selected the year.
        acceptable_years: Years intentionally supported by the dataset.

    Returns:
        The validated year.

    Raises:
        ValueError: If the year is not supported.
    """
    years = tuple(sorted(acceptable_years))
    if year not in years:
        raise ValueError(
            f"Dataset '{dataset_name}' does not support {setting_name}={year}. "
            f"Acceptable years are {list(years)}."
        )
    return year


@overload
def canonicalize_hourly_year(
    data: pd.DataFrame,
    year: int,
    *,
    dataset_name: str,
    preserve_column_totals: bool = False,
) -> pd.DataFrame: ...


@overload
def canonicalize_hourly_year(
    data: pd.Series,
    year: int,
    *,
    dataset_name: str,
    preserve_column_totals: bool = False,
) -> pd.Series: ...


def canonicalize_hourly_year(
    data: DataFrameOrSeries,
    year: int,
    *,
    dataset_name: str,
    preserve_column_totals: bool = False,
) -> DataFrameOrSeries:
    """Convert one complete timestamped calendar year to 8,760 model hours.

    Leap-day hours are removed. When ``preserve_column_totals`` is true, each
    column (or the series) is rescaled to retain its pre-removal annual total.

    Args:
        data: Hourly values indexed by timestamps.
        year: Calendar year represented by ``data``.
        dataset_name: Human-readable source identifier used in errors.
        preserve_column_totals: Whether to restore totals after leap-day removal.

    Returns:
        A copy indexed by the contiguous integer range ``0..8759``.

    Raises:
        TypeError: If the data is not timestamp-indexed.
        ValueError: If timestamps are incomplete, duplicated, or outside ``year``.
    """
    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError(
            f"Dataset '{dataset_name}' must provide a DatetimeIndex before "
            "hourly calendar normalization."
        )

    normalized = data.sort_index().copy()
    index = pd.DatetimeIndex(normalized.index)
    if index.has_duplicates:
        duplicates = index[index.duplicated()].unique()
        raise ValueError(
            f"Dataset '{dataset_name}' contains duplicate timestamps for {year}: "
            f"{duplicates[:5].tolist()}."
        )

    start = pd.Timestamp(year=year, month=1, day=1, tz=index.tz)
    end = pd.Timestamp(year=year + 1, month=1, day=1, tz=index.tz)
    expected = pd.date_range(start, end, freq="1h", inclusive="left")
    missing = expected.difference(index)
    unexpected = index.difference(expected)
    if len(missing) or len(unexpected):
        raise ValueError(
            f"Dataset '{dataset_name}' does not contain a complete hourly year "
            f"{year}. Missing hours: {len(missing)}; unexpected hours: "
            f"{len(unexpected)}."
        )

    original_totals = normalized.sum(axis=0)
    if calendar.isleap(year):
        normalized = normalized.loc[~((index.month == 2) & (index.day == 29))]

    normalized = normalized.reset_index(drop=True)
    normalized.index.name = "time"
    if len(normalized) != MODEL_HOURS_PER_YEAR:
        raise ValueError(
            f"Dataset '{dataset_name}' produced {len(normalized)} model hours for "
            f"{year}; expected {MODEL_HOURS_PER_YEAR}."
        )

    if preserve_column_totals:
        normalized_totals = normalized.sum(axis=0)
        if isinstance(normalized, pd.DataFrame):
            assert isinstance(original_totals, pd.Series)
            assert isinstance(normalized_totals, pd.Series)
            invalid = (normalized_totals == 0) & (original_totals != 0)
            if invalid.any():
                raise ValueError(
                    f"Dataset '{dataset_name}' cannot preserve totals because "
                    "a nonzero profile has a zero total after calendar conversion."
                )
            scale = original_totals.div(normalized_totals).fillna(1)
            normalized = normalized.mul(scale, axis=1)
        else:
            original_total = float(cast(float, original_totals))
            normalized_total = float(cast(float, normalized_totals))
            if normalized_total == 0 and original_total != 0:
                raise ValueError(
                    f"Dataset '{dataset_name}' cannot preserve its nonzero total "
                    "after calendar conversion."
                )
            if normalized_total != 0:
                normalized = normalized * original_total / normalized_total

    return normalized
