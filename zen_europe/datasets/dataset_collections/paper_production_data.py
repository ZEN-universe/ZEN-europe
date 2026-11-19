from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.datasets.datasets.carrier.jrc_bat_paper import JRCBATPaper
from zen_europe.datasets.datasets.carrier.rehfeldt2017 import Rehfeldt2017
from zen_europe.utils.constants import Constants
from zen_europe.utils.industry import model_nodes
from zen_europe.utils.utils import instance_cache

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings

SECTOR = "paper"
# JRC-EU-TIMES processes of the paper sub-processes
JRC_PROCESSES = {
    "paper": "IPPHIGQUA01",
    "recovered_fibres": "IPPLOWQUA01",
    "chemical_pulp": "IPPPUPCHE01",
}


class PaperProductionData(DatasetCollection):
    """Paper production: demand, energy intensity, capacity and costs."""

    name = "paper_production_data"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "industry_production_data": IndustryProductionData(
                self.settings, self.source_path
            ),
            "rehfeldt2017": Rehfeldt2017(self.source_path),
            "jrc_bat_paper": JRCBATPaper(self.source_path),
        }

    # ---------- product ----------

    def get_demand(self, element: Element) -> Attribute:
        """Get the paper demand: today's production."""
        return self._industry.get_demand(
            element,
            self.calculate_production(model_nodes(element)),
            "The production is the JRC-IDEES physical output; for CH, NO and UK, "
            "their consumption from the JRC BAT reference document is used.",
        )

    # ---------- production technology ----------

    def get_input_carrier(self, element: Element) -> Attribute:
        """Get the input carriers of paper production."""
        return self._industry.get_input_carrier(
            element,
            self.calculate_conversion_factors(),
            "The fuels are the JRC-IDEES thermal energy carriers of paper above the "
            "fuel share cut-off.",
        )

    def get_conversion_factor(self, element: Element) -> Attribute:
        """Get the energy demand per tonne of paper."""
        return self._industry.get_conversion_factor(
            element,
            self.calculate_conversion_factors(),
            "The energy intensity is the activity-weighted energy intensity of the "
            "paper sub-processes from Rehfeldt et al. (2017); the fuel above 200 °C "
            "is split by the JRC-IDEES fuel mix.",
        )

    def get_capacity_existing(self, element: Element) -> Attribute:
        """Get the existing paper production capacity."""
        return self._industry.get_capacity_existing(
            element,
            self._calculate_capacity(model_nodes(element)),
            "The existing production capacity is the JRC-IDEES installed capacity "
            "at 8760 hours per year; for CH, NO and UK it is the product demand "
            "divided by "
            f"{self._industry.describe_capacity_utilisation()}.",
        )

    def get_lifetime(self, element: Element) -> Attribute:
        """Get the lifetime from JRC-EU-TIMES."""
        return element.lifetime.set_data(
            default_value=float(self._costs["lifetime"]),
            source=self._jrc_cost_source(),
        )

    def get_capex_specific_conversion(self, element: Element) -> Attribute:
        """Get the investment cost from the literature."""
        capex = self._industry.calculate_literature_cost(SECTOR, "capex")
        return element.capex_specific_conversion.set_data(
            # Euro/(t/a) -> Euro/(t/h)
            default_value=round(capex * Constants.HOURS_PER_YEAR, 2),
            unit="Euro/(tproduct/h)",
            source=AssumptionInformation(
                description=self._industry.describe_literature_cost(SECTOR, "capex")
            ),
        )

    def get_opex_specific_fixed(self, element: Element) -> Attribute:
        """Get the fixed O&M cost from JRC-EU-TIMES."""
        return element.opex_specific_fixed.set_data(
            default_value=float(self._costs["opex_fixed"]),
            unit="Euro/(tproduct/h)",
            source=self._jrc_cost_source(),
        )

    def get_opex_specific_variable(self, element: Element) -> Attribute:
        """Get the variable O&M cost from JRC-EU-TIMES, without energy."""
        return element.opex_specific_variable.set_data(
            default_value=float(self._costs["opex_variable"]),
            unit="Euro/tproduct",
            source=self._jrc_cost_source(),
        )

    # ---------- data used by other collections ----------

    @instance_cache
    def calculate_production(self, nodes: tuple[str, ...]) -> pd.Series:
        """Physical production (t/h): the JRC-IDEES physical output; the JRC BAT
        consumption at CH, NO and UK."""
        industry = self._industry
        production = industry.to_t_per_hour(
            industry.get_industry_physical_output(SECTOR, nodes)
        )
        consumption = cast(JRCBATPaper, self.data["jrc_bat_paper"]).get_consumption()
        production.loc[consumption.index] = industry.to_t_per_hour(consumption)
        return production

    def calculate_demand(self, nodes: tuple[str, ...]) -> pd.Series:
        """Paper demand (t/h): the physical production."""
        return self.calculate_production(nodes).rename("demand").rename_axis("node")

    def calculate_energy_intensity(self) -> pd.Series:
        """Fuel (above 200 °C), heat and electricity demand (GW per t/h) from the
        Rehfeldt et al. (2017) sub-processes."""
        return self._energy_intensity

    def calculate_heat_conversion_factors(self) -> pd.Series:
        """Heat demand per band (GW per t/h)."""
        return self._industry.calculate_heat_conversion_factors(
            SECTOR, self.calculate_energy_intensity()
        )

    def calculate_fuel_shares(self) -> pd.Series:
        """JRC-IDEES fuel mix of paper."""
        return self._industry.calculate_fuel_shares(SECTOR)

    def calculate_conversion_factors(self) -> pd.Series:
        """Energy demand (GW per t/h) per input carrier."""
        return self._industry.calculate_conversion_factors(
            SECTOR, self.calculate_energy_intensity(), self.calculate_fuel_shares()
        )

    # ---------- helpers ----------

    @property
    def _industry(self) -> IndustryProductionData:
        return cast(IndustryProductionData, self.data["industry_production_data"])

    @cached_property
    def _energy_intensity(self) -> pd.Series:
        return self._industry.calculate_energy_intensity_rehfeldt(SECTOR)

    @instance_cache
    def _calculate_capacity(self, nodes: tuple[str, ...]) -> pd.Series:
        """Installed capacity (t/h): JRC-IDEES; the production per capacity
        utilisation at CH, NO and UK."""
        industry = self._industry
        capacity = industry.to_t_per_hour(
            industry.get_industry_installed_capacity(SECTOR, nodes)
        )
        bat_nodes = cast(JRCBATPaper, self.data["jrc_bat_paper"]).get_consumption()
        capacity.loc[bat_nodes.index] = (
            self.calculate_production(nodes).loc[bat_nodes.index]
            / industry.capacity_utilisation
        )
        return capacity

    @cached_property
    def _costs(self) -> dict[str, float]:
        """JRC-EU-TIMES costs of the paper processes, weighted by the Rehfeldt et al.
        (2017) activity."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        return self._industry.calculate_jrc_costs(
            JRC_PROCESSES, rehfeldt.get_activity_weights(SECTOR)
        )

    def _jrc_cost_source(self) -> SourceInformation:
        return SourceInformation(
            description=(
                "JRC-EU-TIMES costs and lifetime of the paper processes, weighted by "
                "the Rehfeldt et al. (2017) activity. "
                + self._industry.describe_inflation()
            ),
            metadata=self.metadata,
        )
