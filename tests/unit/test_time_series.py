"""Tests for explicit year contracts and hourly calendar handling."""

from __future__ import annotations

import ast
import calendar
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pandas as pd
import pytest
from pydantic import ValidationError
from zen_creator.utils.settings import Settings

from zen_europe.utils.time_series import (
    canonicalize_hourly_year,
    require_acceptable_year,
    validate_model_time_index,
)


def _hourly_year(year: int) -> pd.DataFrame:
    index = pd.date_range(
        f"{year}-01-01", f"{year + 1}-01-01", freq="1h", inclusive="left"
    )
    return pd.DataFrame({"profile": 1.0}, index=index)


@pytest.mark.parametrize("year", [2019, 2020])
def test_time_series_year_contract(year: int) -> None:
    """Resolve the weather year to the demand year when no override is set."""
    settings = Settings.model_validate({"time": {"time_series_year": year}})
    assert settings.time.time_series_year == year
    assert settings.time.resolved_weather_year == year


def test_weather_year_override_and_validation() -> None:
    """Accept supported weather overrides and reject unsupported year settings."""
    settings = Settings.model_validate(
        {"time": {"time_series_year": 2019, "weather_year": 2008}}
    )
    assert settings.time.resolved_weather_year == 2008
    with pytest.raises(ValidationError, match="weather_year"):
        Settings.model_validate({"time": {"weather_year": 2007}})
    with pytest.raises(ValidationError, match="time_series_year"):
        Settings.model_validate({"time": {"time_series_year": 2018}})


@pytest.mark.parametrize("year", [2019, 2020])
def test_canonicalize_complete_year(year: int) -> None:
    """Convert complete regular and leap calendar years to 8,760 model hours."""
    result = canonicalize_hourly_year(
        _hourly_year(year), year=year, dataset_name="test"
    )
    assert result.index.equals(pd.RangeIndex(8760, name="time"))
    assert len(result) == 8760


def test_canonicalize_leap_year_can_preserve_total() -> None:
    """Retain an annual total when leap-day hours are removed on request."""
    source = _hourly_year(2020)
    result = canonicalize_hourly_year(
        source,
        year=2020,
        dataset_name="test",
        preserve_column_totals=True,
    )
    assert result["profile"].sum() == pytest.approx(source["profile"].sum())
    assert calendar.isleap(2020)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "wrong_year"])
def test_canonicalize_rejects_invalid_timestamps(defect: str) -> None:
    """Reject incomplete, duplicate, and out-of-year hourly calendars."""
    source = _hourly_year(2019)
    if defect == "missing":
        source = source.iloc[1:]
    elif defect == "duplicate":
        source = pd.concat([source, source.iloc[[0]]])
    else:
        source.index = source.index + pd.DateOffset(years=1)
    with pytest.raises(ValueError):
        canonicalize_hourly_year(source, year=2019, dataset_name="test")


def test_rejected_year_message_identifies_contract() -> None:
    """Report the dataset, setting, rejected year, and supported year range."""
    with pytest.raises(
        ValueError,
        match=r"Dataset 'example'.*weather_year=2007.*2008.*2022",
    ):
        require_acceptable_year(
            2007,
            dataset_name="example",
            setting_name="weather_year",
            acceptable_years=tuple(range(2008, 2023)),
        )


def test_year_consumers_declare_and_validate_contracts() -> None:
    """Prevent new year-setting consumers from bypassing explicit contracts."""
    package = Path(__file__).parents[2] / "zen_europe" / "datasets"
    failures: list[str] = []
    year_names = {"time_series_year", "weather_year", "resolved_weather_year"}
    for path in package.rglob("*.py"):
        if path.name == "time.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in (item for item in ast.walk(tree) if isinstance(item, ast.ClassDef)):
            attributes = {
                item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)
            }
            if not attributes.intersection(year_names):
                continue
            assignments = {
                target.id
                for item in node.body
                if isinstance(item, (ast.Assign, ast.AnnAssign))
                for target in (
                    item.targets if isinstance(item, ast.Assign) else [item.target]
                )
                if isinstance(target, ast.Name)
            }
            calls = {
                item.func.id
                for item in ast.walk(node)
                if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
            }
            if "ACCEPTABLE_YEARS" not in assignments:
                failures.append(f"{path.name}:{node.name} lacks ACCEPTABLE_YEARS")
            if "require_acceptable_year" not in calls:
                failures.append(f"{path.name}:{node.name} lacks runtime validation")
    assert failures == []
