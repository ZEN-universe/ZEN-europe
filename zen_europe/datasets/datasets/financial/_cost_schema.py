"""Shared schema for technology-cost datasets (DEA, TYNDP, DIW, LUW, EUREF).

Every agency dataset in this package parses its own raw source file(s) into a
long-format ``pd.DataFrame`` using this schema, so that
:class:`~zen_europe.datasets.dataset_collections.technology_cost_database.TechnologyCostDatabase`
can concatenate and average across agencies without agency-specific logic.

Index (5-level MultiIndex): ``technology, plant_size, scenario, variable, year``
    - ``technology``: internal ZEN-europe technology name (or a source-specific
      sub-type not modeled as its own technology yet, e.g.
      ``wind_offshore_near_shore``).
    - ``plant_size``: one of :data:`PLANT_SIZES`. Agencies without a size
      dimension in their source data report everything under ``"M"``.
    - ``scenario``: one of :data:`SCENARIOS`.
    - ``variable``: one of :data:`COST_VARIABLES` (money-valued) or
      :data:`TECH_VARIABLES` (physical, no currency conversion needed).
    - ``year``: reporting year, one of (a subset of) :data:`YEARS`.

Columns:
    - ``value``: value converted to the standard unit for that variable
      (see :data:`STANDARD_UNITS`), but *not* yet inflation/currency-adjusted.
      For ``variable`` in :data:`TECH_VARIABLES` this is the final value.
    - ``unit``: the standard unit (:data:`STANDARD_UNITS`).
    - ``money_year_src``: native reporting year of the source value, used to
      rebase ``value`` to a target money-year via
      ``ECBInflation.get_inflation_rate``. ``NaN`` for tech variables.
    - ``value_src`` / ``unit_src``: original source value/unit, kept for
      traceability and debugging.
"""

from __future__ import annotations

# Target year grid (matches the legacy `CostHelpers.get_years()`: 2015-2050 in
# 5-year steps). Agencies with sparser source data simply report a subset.
YEARS: list[int] = list(range(2015, 2050 + 5, 5))

PLANT_SIZES: tuple[str, ...] = ("S", "M", "L")
SCENARIOS: tuple[str, ...] = ("min", "ref", "max")

COST_VARIABLES: tuple[str, ...] = ("capex", "capex_energy", "fopex", "vopex")
TECH_VARIABLES: tuple[str, ...] = ("efficiency", "lifetime", "construction_time")

# `capex_energy` is the investment cost of a storage technology's energy
# capacity; `capex` is its power capacity, on the same basis as every other
# technology.
STANDARD_UNITS: dict[str, str] = {
    "capex": "Euro/kW",
    "capex_energy": "Euro/kWh",
    "fopex": "Euro/kW",
    "vopex": "Euro/MWh",
    "efficiency": "1",
    "lifetime": "1",
    "construction_time": "1",
}

# A handful of DEA technologies (carbon capture) are sized by CO2 throughput
# rather than power/heat capacity, so their capex/fopex/vopex are reported on
# a Euro/tCO2 basis instead of Euro/kW. `TechnologyCostDatabase` reads the
# actual unit back out of the data rather than assuming `STANDARD_UNITS`, so
# these technologies mix in transparently; listed here only for documentation
# and so a `Dataset` can look up which convention it must produce.
CO2_BASIS_TECHNOLOGIES: frozenset[str] = frozenset(
    {"DAC", "cement_post_comb", "NG_DRI_CCS", "BF_BOF_CCS", "SMR_CCS"}
)
CO2_BASIS_UNITS: dict[str, str] = {
    "capex": "Euro/(tCO2/h)",
    "fopex": "Euro/(tCO2/h)",
    "vopex": "Euro/tCO2",
}

INDEX_NAMES: list[str] = ["technology", "plant_size", "scenario", "variable", "year"]
VALUE_COLUMNS: list[str] = ["value", "unit", "money_year_src", "value_src", "unit_src"]
