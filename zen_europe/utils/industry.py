"""Names and helpers shared by the industry heat sectors, see docs, "Industry heat
sectors"."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
)

if TYPE_CHECKING:
    import pandas as pd
    from zen_creator import Element

# year of the production, energy and heat statistics
DATA_YEAR = 2023
SECTORS = ("glass", "ceramic", "paper", "food")
HEAT_LEVELS = ("0_100", "100_150", "150_200")
HEAT_SOURCES = ("waste_heat", "water")
BOILER_FUELS = ("biomass", "natural_gas", "electrode", "oil", "coal", "waste")
# proxy node of the nodes without JRC-IDEES data: CH as AT, NO as FI, UK as DE
PROXY_NODES = {"CH": "AT", "NO": "FI", "UK": "DE"}
NODES_WITHOUT_IDEES = tuple(PROXY_NODES)
# JRC-IDEES region of the EU27 aggregate
IDEES_EU = "EU27"


def heat_carrier(level: str, sector: str) -> str:
    """Heat carrier of a sector's temperature band."""
    return f"heat_industry_{level}_{sector}"


def kiln_fuel(sector: str) -> str:
    """Kiln fuel carrier of a sector."""
    return f"kiln_fuel_{sector}"


def model_nodes(element: Element) -> tuple[str, ...]:
    """Nodes of the element's model."""
    return tuple(element.model.config.system.set_nodes)


def spread_capacity_existing(capacity: pd.Series, element: Element) -> pd.Series:
    """Spread today's capacity per node over its construction years, as for all
    other technologies."""
    frame = capacity.to_frame(element.settings.time.reference_year - 1)
    frame = calculate_capacity_addition_from_cumulative(frame, element)
    return format_capacity_existing(frame)
