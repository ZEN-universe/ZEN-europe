import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar, Union, cast, overload

import numpy as np
import pandas as pd
from zen_creator import Technology

MIN_CAPACITY_ADDITION = 1e-5

F = TypeVar("F", bound=Callable[..., Any])


def instance_cache(method: F) -> F:
    """Memoize a method per instance, keyed by its arguments."""

    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            cache = self._instance_cache
        except AttributeError:
            cache = {}
            self._instance_cache = cache
        key = (method.__name__, args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = method(self, *args, **kwargs)
        return cache[key]

    return cast(F, wrapper)


# maps the country names used in the raw source file to NUTS0 node codes,
def convert_country_names(series: pd.Series) -> pd.Series:
    """this method converts a series of country names into the node names used here."""
    country_names = {
        "Austria": "AT",
        "Belgium": "BE",
        "Bulgaria": "BG",
        "Switzerland": "CH",
        "Czech Republic": "CZ",
        "Czechia": "CZ",
        "Germany": "DE",
        "Denmark": "DK",
        "Estonia": "EE",
        "Greece": "EL",
        "GR": "EL",
        "Spain": "ES",
        "Finland": "FI",
        "France": "FR",
        "Croatia": "HR",
        "Hungary": "HU",
        "Ireland": "IE",
        "Italy": "IT",
        "Lithuania": "LT",
        "Luxembourg": "LU",
        "Latvia": "LV",
        "The Netherlands": "NL",
        "Netherlands": "NL",
        "Netherlands (Kingdom of the)": "NL",
        "Norway": "NO",
        "Poland": "PL",
        "Portugal": "PT",
        "Romania": "RO",
        "Sweden": "SE",
        "Slovenia": "SI",
        "Slovakia": "SK",
        "Slovak Republic": "SK",
        "United Kingdom": "UK",
        "United Kingdom of Great Britain and Northern Ireland": "UK",
        "Great Britain": "UK",
        "UK": "UK",
    }
    series_new = series.apply(
        lambda el: country_names[el] if el in country_names.keys() else None
    )
    return series_new


def convert_ISO3_to_ISO2(series: pd.Series):
    """this method converts a series of ISO3 country codes into ISO2 country codes."""
    iso3_to_iso2 = {
        "AUT": "AT",
        "BEL": "BE",
        "BGR": "BG",
        "CHE": "CH",
        "CZE": "CZ",
        "DEU": "DE",
        "DNK": "DK",
        "EST": "EE",
        "GRC": "EL",
        "ESP": "ES",
        "FIN": "FI",
        "FRA": "FR",
        "HRV": "HR",
        "HUN": "HU",
        "IRL": "IE",
        "ITA": "IT",
        "LTU": "LT",
        "LUX": "LU",
        "LVA": "LV",
        "NLD": "NL",
        "NOR": "NO",
        "POL": "PL",
        "PRT": "PT",
        "ROU": "RO",
        "SWE": "SE",
        "SVN": "SI",
        "SVK": "SK",
        "GBR": "UK",
        "ISL": "IS",
    }
    series_new = series.apply(
        lambda el: iso3_to_iso2[el] if el in iso3_to_iso2.keys() else None
    )
    return series_new


def link_lng_countries() -> dict:
    lng_link = {
        "lng_russia": ["LNG Russia"],
        "lng": [
            "LNG Middle East",
            "LNG North Africa",
            "LNG North America",
            "LNG Others",
        ],
    }
    return lng_link


def link_natural_gas_countries() -> dict:
    natural_gas_link = {
        ("Algeria", "Libya"): ["ES", "IT"],
        ("Azerbaijan", "Turkey", "Turkmenistan"): ["EL"],
        ("Russia"): ["BG", "RO", "HU", "SK", "PL", "LT", "EE", "DE", "FI"],
    }
    return natural_gas_link


@overload
def interpolate_missing_years(df: pd.DataFrame) -> pd.DataFrame: ...
@overload
def interpolate_missing_years(df: pd.Series) -> pd.Series: ...
def interpolate_missing_years(
    df: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    """Interpolate missing years in a DataFrame or Series.

    Args:
        df: DataFrame with years as columns, or Series with years as index.

    Returns:
        The input with missing years interpolated.
    """
    if isinstance(df, pd.DataFrame):
        assert (
            all(isinstance(col, int) for col in df.columns)
            and df.columns.dtype == "int64"
        ), "All columns must be numeric (years)."
        # Reindex the columns to include all years from min to max
        first_year = cast(int, df.columns.min())
        last_year = cast(int, df.columns.max())
        df = df.reindex(range(first_year, last_year + 1), axis=1).interpolate(axis=1)
    elif isinstance(df, pd.Series):
        assert (
            all(isinstance(idx, int) for idx in df.index) and df.index.dtype == "int64"
        ), "All index values must be numeric (years)."
        # Reindex the index to include all years from min to max
        first_index = cast(int, df.index.min())
        last_index = cast(int, df.index.max())
        df = df.reindex(range(first_index, last_index + 1)).interpolate()
    else:
        raise TypeError(
            "Input must be a pandas DataFrame or Series,"
            f" but got {type(df).__name__}."
        )
    return df


def linearly_fill_missing_years(
    df: pd.DataFrame, deg: int = 1, clip_to_zero: bool = True
) -> pd.DataFrame:
    """Fill missing years by fitting a polynomial to each row.

    In contrast to :func:`interpolate_missing_years`, which only interpolates
    between observed values, this fits a (by default linear) trend through the
    observed years of each row and uses it to fill the gaps, including the
    years before the first and after the last observation. Rows with fewer than
    two observations are left untouched.

    Args:
        df (pd.DataFrame): DataFrame with years as columns.
        deg (int): Degree of the polynomial fitted to each row.
        clip_to_zero (bool): Whether to clip the filled values at zero.

    Returns:
        pd.DataFrame: DataFrame with missing years filled.
    """
    df_filled = df.copy()

    def fit_row(row: pd.Series) -> Any:
        """Polynomial coefficients of a row, or None if it has too few values."""
        if len(row.dropna()) > 1:
            return np.polyfit(row.dropna().index, row.dropna(), deg=deg)
        return None

    fit_params = df.apply(fit_row, axis=1)
    df_fit = df.apply(
        lambda row: (
            np.polyval(fit_params.loc[row.name], row.index)
            if fit_params.loc[row.name] is not None
            else row
        ),
        axis=1,
        result_type="expand",
    )
    df_fit.columns = df.columns
    df_filled[df_filled.isna()] = df_fit[df_filled.isna()]
    if clip_to_zero:
        df_filled = df_filled.clip(lower=0)
    return df_filled


def calculate_capacity_addition_from_cumulative(
    df: pd.DataFrame, element: Technology
) -> pd.DataFrame:
    """Calculate capacity addition from cumulative capacity data.

    Args:
        df (pd.DataFrame): DataFrame with cumulative capacity data.
        element (Technology): The conversion technology element.

    Returns:
        pd.DataFrame: DataFrame with capacity addition data.
    """
    df = divide_evolution_of_cumulative_capacity(df)
    df = account_for_decommissioned_capacity(df, element)
    return df


def divide_evolution_of_cumulative_capacity(df: pd.DataFrame) -> pd.DataFrame:
    """Divide the evolution of the cumulative capacity into capacity additions.
    We calculate the capacity addition by taking the difference between consecutive
    years.
    We start at the last year and move backwards, so that we can account for
    decommissioned capacity.
    If the capacity diff is positive, it is a capacity addition. If it is negative,
    it is a decommissioned capacity, which we subtract from the first year of the
    cumulative capacity data.
    The first year then represents the total capacity that was available in that year,
    corrected for decommissioned capacity.
    Args:
        df (pd.DataFrame): DataFrame with cumulative capacity data.

    Returns:
        pd.DataFrame: DataFrame with capacity addition data.
    """
    df = df.astype(float)
    df = df.sort_index(axis=1, ascending=True)
    # take difference
    df[df.columns[1:]] = df.diff(axis=1)[df.columns[1:]]
    # decommissioned capacity
    decom_capa = df.clip(upper=0)
    total_decom_capa = decom_capa.sum(axis=1)
    # capacity additions
    df = df.clip(lower=0)
    # subtract decommissioned capacity from existing capa in first time step
    df[df.columns[0]] += total_decom_capa
    for col in df.columns.sort_values(ascending=True):
        if col != df.columns.max():
            pos_col = df[col].clip(lower=0)
            neg_col = df[col].clip(upper=0)
            if (neg_col.dropna() == 0).all():
                break
            df[cast(int, col) + 1] += neg_col
            df[col] = pos_col

    return df


def account_for_decommissioned_capacity(
    df: pd.DataFrame, element: Technology
) -> pd.DataFrame:
    """Account for decommissioned capacity.
    The value in the first year of the capacity dataframe is assumed to have been built
    steadily over the previous lifetime of the technology.
    Thus, we divide the value in the first year by the lifetime of the technology and
    add this value to the previous years, so that we can account for decommissioned
    capacity.
    Any capacity built in year x must be decommissioned in year x + lifetime,
    so we add the decommissioned capacity to the dataframe, shifted by the lifetime.

    Args:
        df (pd.DataFrame): DataFrame with cumulative capacity data.

    Returns:
        pd.DataFrame: DataFrame with decommissioned capacity accounted for.
    """

    df.columns = df.columns.astype(int)
    if df.columns.min() >= element.settings.time.reference_year:
        logging.warning(
            f"The first year of the capacity data for {element.name} is "
            f"{df.columns.min()}, which is greater than or equal to the reference year "
            f"{element.settings.time.reference_year}.\n"
            "There is no capacity built before the reference year."
        )
    df = df.sort_index(axis=1)
    # get years
    start_year = cast(int, df.columns.min())
    reference_year = element.settings.time.reference_year
    lifetime_value = cast(float, element.lifetime.default_value)
    assert int(lifetime_value) == lifetime_value, "Lifetime must be an integer"
    lifetime = int(lifetime_value)
    relevant_lifetime = (
        lifetime
        - element.settings.time.interval_between_years
        - int(cast(float, element.construction_time.default_value))
    )
    lifetime_years = list(range((reference_year) - relevant_lifetime, reference_year))
    earlier_years = list(range((start_year + 1) - relevant_lifetime, start_year + 1))
    combined_years = df.columns.union(earlier_years).sort_values()
    # allocate the existing units of years before the lifetime to first year of lifetime
    # extended capacity df
    df_ext = pd.DataFrame(index=df.index, columns=combined_years, dtype=float)
    df_ext[df.columns] = df
    # divide capacity in first year by lifetime
    df_ext[start_year] /= relevant_lifetime
    # fill previous years by
    df_ext = df_ext.bfill(axis=1)
    # decommissioned capacity
    df_decom = df_ext.copy()
    df_decom.columns = cast(pd.Index, df_ext.columns) + lifetime
    # add decommissioned capacity
    df_tot = df_ext.add(df_decom, fill_value=0)
    # only choose lifetime years
    common_years = cast(pd.Index, df_tot.columns).intersection(lifetime_years)
    df_tot = df_tot[common_years]
    # scale to match total capacity again
    df_tot = df_tot[df_tot.sum(axis=1) != 0]
    df = df[df.sum(axis=1) != 0]
    df_tot = df_tot.mul(
        df.loc[:, : reference_year - 1].sum(axis=1) / df_tot.sum(axis=1), axis=0
    )
    return df_tot


def format_capacity_existing(df: Union[pd.DataFrame, pd.Series]) -> pd.Series:
    """Format the existing capacity data to match the expected format.

    Args:
        df (pd.DataFrame, pd.Series): DataFrame or Series with existing capacity data.
    Returns:
        pd.Series: Formatted Series with existing capacity data.
    """
    if isinstance(df, pd.DataFrame):
        df = cast(pd.Series, df.stack())
    df = df[df >= MIN_CAPACITY_ADDITION]
    df.index.names = ["node", "year_construction"]
    df.name = "capacity_existing"
    return df
