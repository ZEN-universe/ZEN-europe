from __future__ import annotations

from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class CacheSettings(SettingsCategory):
    """Settings controlling which dataset caches are reloaded from source and
    overwritten on disk, instead of being read from an existing cache file."""

    name: ClassVar[str] = "cache"

    overwrite_dea: bool = False
    overwrite_entsoe: bool = False
    overwrite_eurostat: bool = False
    overwrite_eea_ghg_inventory: bool = False
    overwrite_global_carbon_budget: bool = False
    overwrite_desnz_ghg_inventory: bool = False
    overwrite_worldbank_co2_emissions: bool = False
    overwrite_worldbank_population: bool = False
    overwrite_ecb: bool = False
    overwrite_jrc_idees: bool = False
    overwrite_unece: bool = False
    overwrite_pan_european_climate_database: bool = False
    overwrite_passenger_cars_cox: bool = False
    overwrite_dac_costs_sievert: bool = False


_active = CacheSettings()


def set_active_cache_settings(settings: CacheSettings) -> None:
    """Set the process-wide cache settings that dataset cache checks read.

    Datasets that receive `settings` directly (e.g. via dependency injection)
    can read `settings.cache` instead. This accessor is for datasets that do
    not, so that the overwrite flags do not have to be threaded through every
    dataset constructor and call site.
    """
    global _active
    _active = settings


def get_active_cache_settings() -> CacheSettings:
    """Return the process-wide cache settings, defaulting to all-False."""
    return _active
