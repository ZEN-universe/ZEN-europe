"""Names and helpers shared by the industry heat sectors, see docs, "Industry heat
sectors"."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


def heat_carrier(level: str) -> str:
    """Heat carrier of a temperature band, shared by all industry heat sectors."""
    return f"heat_industry_{level}"


def sector_fuel(sector: str) -> str:
    """Kiln or furnace fuel carrier of a sector."""
    return f"{sector}_fuel"


def model_nodes(element: Element) -> tuple[str, ...]:
    """Nodes of the element's model."""
    return tuple(element.model.config.system.set_nodes)


def model_sectors(element: Element) -> tuple[str, ...]:
    """Industry heat sectors of the element's model."""
    return tuple(sector for sector in SECTORS if sector in element.model.sectors)
