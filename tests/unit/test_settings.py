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


def test_settings_override_from_dict() -> None:
    settings = Settings.model_validate({"time": {"interval_between_years": 5}})

    assert settings.time.interval_between_years == 5


def test_settings_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"time": {"interval_between_years": "five"}})


def test_settings_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"time": {"bogus_field": 1}})


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
