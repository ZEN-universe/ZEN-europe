"""Unit tests for ZEN-europe's concrete settings categories.

These are registered as zen_creator SettingsCategory subclasses (see
zen_europe/settings/) and become queryable as model.settings.<name>.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from zen_creator.utils.config import Config
from zen_creator.utils.settings import Settings

import zen_europe.settings  # noqa: F401  (registers the categories)

CONFIG_PATH = Path(__file__).parents[2] / "data" / "zen_europe_config.yaml"


def test_time_settings_defaults() -> None:
    settings = Settings()

    assert settings.time.interval_between_years == 4
    assert settings.time.reference_year == 2022
    assert settings.time.last_year == 2050


def test_investment_settings_defaults() -> None:
    settings = Settings()

    assert settings.investment.allow_investment is True
    assert settings.investment.knowledge_depreciation_rate == 0.1


def test_settings_override_from_dict() -> None:
    settings = Settings.model_validate({"time": {"interval_between_years": 5}})

    assert settings.time.interval_between_years == 5
    assert settings.time.reference_year == 2022


def test_settings_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"time": {"interval_between_years": "five"}})


def test_settings_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"time": {"bogus_field": 1}})


def test_config_yaml_loads_time_settings() -> None:
    settings = Settings.load_from_yaml(CONFIG_PATH)

    assert settings.time.reference_year == 2022
    assert settings.time.interval_between_years == 4


def test_optimized_years_follows_from_the_horizon() -> None:
    """2022 to 2050 in steps of 4 is 8 optimized years."""
    settings = Settings()

    assert settings.time.optimized_years == 8


def test_optimized_years_warns_on_an_uneven_horizon(caplog) -> None:
    """A horizon that is not a multiple of the interval is reported."""
    settings = Settings.model_validate({"time": {"interval_between_years": 3}})

    assert settings.time.optimized_years == 10
    assert "last optimized year is 2049" in caplog.text


def test_data_years_covers_every_calendar_year() -> None:
    """The written data is indexed by year, not by optimized year."""
    settings = Settings()

    data_years = settings.time.years

    assert data_years[0] == 2022
    assert data_years[-1] == 2050
    assert len(data_years) == 29


def test_settings_control_the_system_config() -> None:
    """The controlled values reach the config without being restated there."""
    config = Config.load_from_yaml(CONFIG_PATH)
    settings = Settings.load_from_yaml(CONFIG_PATH)

    settings.apply(config)

    assert config.system.reference_year == 2022
    assert config.system.interval_between_years == 4
    assert config.system.optimized_years == 8
    assert config.system.allow_investment is True
    assert config.system.use_capacities_existing is True
    assert config.system.run_default_scenario is True


def test_config_yaml_may_not_restate_a_controlled_value(tmp_path: Path) -> None:
    """Setting a controlled value under `system:` is rejected."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "system:\n  set_nodes: [CH]\n  reference_year: 2022\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="controlled by the settings field"):
        Config.load_from_yaml(config_path)


if __name__ == "__main__":
    pytest.main([__file__])
