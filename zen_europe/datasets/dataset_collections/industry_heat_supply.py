from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.bfe_industry import BFEIndustry
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.jrc_idees import JRCIDEES
from zen_europe.datasets.datasets.technology.industry_general_assumptions import (
    IndustryGeneralAssumptions,
)
from zen_europe.utils.industry import (
    BOILER_FUELS,
    DATA_YEAR,
    HEAT_LEVELS,
    HEAT_SOURCES,
    IDEES_EU,
    NODES_WITHOUT_IDEES,
    SECTORS,
    kiln_fuel,
    model_nodes,
    spread_capacity_existing,
)
from zen_europe.utils.utils import instance_cache

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings

logger = logging.getLogger(__name__)

# boilers with an existing fleet; no existing electrode boilers
COMBUSTION_FUELS = [fuel for fuel in BOILER_FUELS if fuel != "electrode"]
# Eurostat aggregate for nodes without paper biomass and waste data
EUROSTAT_EU = "EU27_2020"


class IndustryHeatSupply(DatasetCollection):
    """Existing capacities and limits of the industry heat supply technologies."""

    name = "industry_heat_supply"

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
            "eurostat": Eurostat(self.settings, self.source_path),
            "bfe_industry": BFEIndustry(self.source_path),
            "jrc_idees": JRCIDEES(self.source_path),
            "technology_cost_database": TechnologyCostDatabase(
                self.settings, self.source_path
            ),
            "industry_general_assumptions": IndustryGeneralAssumptions(
                self.source_path
            ),
        }

    # ---------- boilers ----------

    def get_capacity_existing_boiler(self, element: Element) -> Attribute:
        """
        Get the existing capacity of an industrial boiler.

        The sector's heat demand is split by the sector's JRC-IDEES fuel mix in
        the node (BFE for CH).
        """
        capacity = self._calculate_boiler_capacity(model_nodes(element)).loc[
            element.sector, element.fuel
        ]
        # drop the smallest boilers of a node
        min_capacity = self._assumptions.get_value("min_boiler_capacity")
        capacity = capacity.where(capacity >= min_capacity, 0.0)
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            df=spread_capacity_existing(capacity, element),
            source=SourceInformation(
                description=(
                    "The existing boiler capacity equals the sector's heat demand "
                    "(0-200 °C), split by the sector's JRC-IDEES fuel mix in the "
                    "country (EU27 for NO and UK; BFE industry fuel mix for CH). "
                    "'Biomass and waste' is biomass, except in paper, where it is "
                    "split by the Eurostat paper industry final consumption "
                    "(FC_IND_PPP_E). There are no existing electrode boilers. Boilers "
                    f"below {min_capacity} GW per node (general industry assumptions) "
                    "are dropped; the capacity is assumed to be built evenly over the "
                    "lifetime of the technology."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- heat pumps ----------

    def get_capex_specific_conversion_heat_pump(self, element: Element) -> Attribute:
        """Get the DEA investment cost, plus waste-heat recovery for waste-heat heat
        pumps."""
        tech_db = cast(TechnologyCostDatabase, self.data["technology_cost_database"])
        capex = tech_db.get_capex_specific_conversion(
            element, proxy_element_name=element.cost_proxy
        )
        if element.heat_source != "waste_heat":
            return capex
        recovery = self._assumptions.get_value("waste_heat_recovery_capex")
        return capex.set_data(
            default_value=capex.default_value + recovery,
            df=None if capex.df is None else capex.df + recovery,
            source=AssumptionInformation(
                description=(
                    f"The DEA investment cost of '{element.cost_proxy}' (Danish Energy "
                    "Agency, Technology Data for Industrial Process Heat, "
                    "https://www.ens.dk/technologydata) plus an assumed "
                    f"{recovery} Euro/kW for the waste-heat recovery, "
                    + self._assumptions.get_description("waste_heat_recovery_capex")
                ),
            ),
        )

    def get_capacity_limit_heat_pump(self, element: Element) -> Attribute:
        """Get the first-year cap (share of band demand) and, for waste heat, the
        sector's waste heat in the band."""
        nodes = pd.Index(model_nodes(element), name="node")
        years = pd.Index(self.settings.time.years, name="year")
        limit = pd.Series(np.inf, index=nodes)
        description = ""
        if element.heat_source == "waste_heat":
            production = self._production_data
            sector = element.sector
            heat = production.calculate_heat_conversion_factors(sector)
            share = heat[element.temp_level] / heat[list(HEAT_LEVELS)].sum()
            fuel = production.calculate_energy_intensity(sector)["fuel"]
            waste_heat = (
                production.calculate_production(sector, tuple(nodes)) * fuel * share
            )
            limit = waste_heat.reindex(nodes, fill_value=0.0)
            description = (
                "Waste heat of processes > 200 °C (their fuel demand), split by band "
                "heat demand. "
            )
        first_share = self._assumptions.get_value("hp_share_first_year")
        demand = self._calculate_band_demand(tuple(nodes)).loc[
            (element.sector, element.temp_level)
        ]
        first_year = (
            demand.reindex(nodes, fill_value=0.0) * first_share / len(HEAT_SOURCES)
        )
        limit = pd.DataFrame({year: limit for year in years})
        limit[years[0]] = np.minimum(limit[years[0]], first_year)
        return element.capacity_limit.set_data(
            default_value=np.inf,
            unit="GW",
            df=limit.stack()
            .rename_axis(["node", "year"])
            .rename("capacity_limit")
            .to_frame(),
            source=SourceInformation(
                description=(
                    description
                    + f"{years[0]}: at most {first_share:.0%} of band demand per node "
                    "(general industry assumptions), split by heat source."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_addition_unbounded_heat_pump(
        self, element: Element, fleet: float
    ) -> Attribute:
        """Get the seed: annual build-out of the DH heat pump `fleet` (GW), split by
        sector-band demand share, heat source and node."""
        nodes = model_nodes(element)
        demand = self._calculate_band_demand(nodes).sum(axis=1)
        share = demand[element.sector, element.temp_level] / demand.sum()
        heat_sources = len(HEAT_SOURCES)
        interval = self.settings.time.interval_between_years
        seed_years = self._assumptions.get_value("hp_seed_years")
        return element.capacity_addition_unbounded.set_data(
            default_value=(
                fleet / seed_years * interval * share / heat_sources / len(nodes)
            ),
            unit="GW",
            source=SourceInformation(
                description=(
                    f"Annual build-out of the DH heat pumps (fleet / {seed_years} yr, "
                    "general industry assumptions) per period, split by sector-band "
                    "demand share, heat source and node, see docs, 'Diffusion'."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- temperature cascade ----------

    def get_capacity_existing_temp_conversion(self, element: Element) -> Attribute:
        """Get today's heat flow down the cascade: all lower bands are supplied by
        boilers."""
        capacity = self._calculate_heat_demand(
            element.sector, element.served_levels, model_nodes(element)
        )
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            df=spread_capacity_existing(capacity, element),
            source=SourceInformation(
                description=(
                    "The existing capacity equals the heat demand of the lower "
                    "bands, which today's boilers supply."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_limit_temp_conversion(self, element: Element) -> Attribute:
        """Get the heat demand of the lower bands times the capacity limit margin."""
        capacity = self._calculate_heat_demand(
            element.sector, element.served_levels, model_nodes(element)
        )
        return self._set_capacity_limit(element, capacity)

    # ---------- thermal energy storage ----------

    def get_capacity_limit_tes(self, element: Element) -> Attribute:
        """Get the heat demand of the storage's band and all lower bands times the
        capacity limit margin, 0 at nodes without demand."""
        levels = HEAT_LEVELS[: HEAT_LEVELS.index(element.temp_level) + 1]
        nodes = model_nodes(element)
        demand = self._calculate_heat_demand(element.sector, levels, nodes)
        return self._set_capacity_limit(
            element,
            demand,
            description=(
                "The flat heat demand of the storage's band and all lower bands "
                "(reachable via the temperature cascade)"
            ),
            nodes=nodes,
        )

    # ---------- kiln fuel ----------

    def get_capacity_existing_kiln_fuel(self, element: Element) -> Attribute:
        """Get today's kiln natural gas demand; none for the alternative fuels."""
        if element.fuel != "natural_gas":
            return element.capacity_existing.set_data(
                default_value=0.0,
                unit="GW",
                source=SourceInformation(
                    description=(
                        "There is no existing capacity of alternative kiln fuels."
                    ),
                    metadata=self.metadata,
                ),
            )
        production = self._production_data
        capacity = production.calculate_production(
            element.sector, model_nodes(element)
        ) * self._kiln_fuel_intensity(element)
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            df=spread_capacity_existing(capacity, element),
            source=SourceInformation(
                description=(
                    "The existing capacity equals the kiln natural gas demand of "
                    "today's production."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_limit_kiln_fuel(self, element: Element) -> Attribute:
        """Get the kiln fuel demand times the capacity limit margin, natural gas
        only."""
        if element.fuel != "natural_gas":
            return element.capacity_limit.set_data(
                default_value=np.inf,
                unit="GW",
                source=SourceInformation(
                    description="The alternative kiln fuels are not limited.",
                    metadata=self.metadata,
                ),
            )
        production = self._production_data
        demand = production.calculate_demand(
            element.sector, model_nodes(element)
        ) * self._kiln_fuel_intensity(element)
        return self._set_capacity_limit(element, demand)

    # ---------- helpers ----------

    @property
    def _production_data(self) -> IndustryProductionData:
        return cast(IndustryProductionData, self.data["industry_production_data"])

    @property
    def _assumptions(self) -> IndustryGeneralAssumptions:
        return cast(
            IndustryGeneralAssumptions, self.data["industry_general_assumptions"]
        )

    def _set_capacity_limit(
        self,
        element: Element,
        demand: pd.Series,
        description: str = "The flat demand",
        nodes: tuple[str, ...] | None = None,
    ) -> Attribute:
        """Limit a technology to the demand times the capacity limit margin, see
        docs, 'Diffusion'. With `nodes`, the limit is 0 at nodes without demand."""
        margin = self._assumptions.get_value("capacity_limit_margin")
        limit = demand * margin
        description = (
            f"{description} times the capacity limit margin of {margin} (general "
            "industry assumptions), see docs, 'Diffusion'."
        )
        if nodes is not None:
            limit = limit.reindex(pd.Index(nodes, name="node")).fillna(0.0)
            description += " 0 at nodes without demand."
        return element.capacity_limit.set_data(
            default_value=np.inf,
            unit="GW",
            df=limit.rename("capacity_limit").to_frame(),
            source=SourceInformation(
                description=description,
                metadata=self.metadata,
            ),
        )

    def _kiln_fuel_intensity(self, element: Element) -> float:
        return self._production_data.calculate_fuel_intensity(element.sector)[
            kiln_fuel(element.sector)
        ]

    def _calculate_heat_demand(
        self, sector: str, levels: tuple[str, ...], nodes: tuple[str, ...]
    ) -> pd.Series:
        """Heat demand (GW) of the sector's products in the given bands."""
        return self._calculate_band_demand(nodes).loc[sector].loc[list(levels)].sum()

    @instance_cache
    def _calculate_band_demand(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Heat demand (GW) per sector and band (rows) and node (columns)."""
        production = self._production_data
        demand = {
            (sector, level): production.calculate_demand(sector, nodes) * heat
            for sector in SECTORS
            for level, heat in production.calculate_heat_conversion_factors(
                sector
            ).items()
        }
        return pd.DataFrame(demand).T.rename_axis(["sector", "level"])

    @instance_cache
    def _calculate_boiler_capacity(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Boiler capacity (GW) per sector and node (rows) and fuel (columns): the
        sector's heat demand split by its fuel mix."""
        production = self._production_data
        # product demand basis, as the heat carriers
        demand = pd.concat(
            {
                sector: production.calculate_demand(sector, nodes)
                * production.calculate_energy_intensity(sector)["heat"]
                for sector in SECTORS
            },
            names=["sector", "node"],
        )
        shares = self._calculate_sector_fuel_shares(nodes)
        return shares.mul(demand.reindex(shares.index, fill_value=0.0), axis=0)

    def _calculate_sector_fuel_shares(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Boiler fuel mix per sector and node (JRC-IDEES, else EU27; BFE for CH)."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        countries = [
            IDEES_EU if node in NODES_WITHOUT_IDEES else node for node in nodes
        ]
        node_index = pd.Index(list(nodes), name="node")
        paper_waste_share = self._calculate_paper_waste_share(nodes)
        shares = {}
        for sector in SECTORS:
            thermal = idees.get_industry_thermal_final_energy_by_fuel(
                sector, DATA_YEAR, "boiler"
            ).loc[countries]
            thermal.index = node_index
            fuels = thermal.reindex(columns=list(BOILER_FUELS), fill_value=0.0)
            # JRC-IDEES reports biomass and waste as one carrier; only the paper
            # industry burns waste (sludge, rejects)
            biomass_and_waste = thermal.get("biomass_and_waste", 0.0)
            waste_share = paper_waste_share if sector == "paper" else 0.0
            fuels["biomass"] += biomass_and_waste * (1.0 - waste_share)
            fuels["waste"] += biomass_and_waste * waste_share
            total = fuels.sum(axis=1)
            fuels = fuels.div(total.where(total > 0), axis=0)
            # equal shares if the sector consumes no fuel at the node
            fuels[COMBUSTION_FUELS] = fuels[COMBUSTION_FUELS].fillna(
                1.0 / len(COMBUSTION_FUELS)
            )
            shares[sector] = fuels.fillna(0.0)
        shares = pd.concat(shares, names=["sector", "node"])
        # CH: fuel mix of the BFE industry branches for all sectors
        if "CH" in nodes:
            bfe = cast(BFEIndustry, self.data["bfe_industry"])
            ch = bfe.get_fuel_consumption(DATA_YEAR).reindex(
                BOILER_FUELS, fill_value=0.0
            )
            ch_rows = shares.index.get_level_values("node") == "CH"
            shares.loc[ch_rows] = (ch / ch.sum()).to_numpy()
        return shares[list(BOILER_FUELS)]

    def _calculate_paper_waste_share(self, nodes: tuple[str, ...]) -> pd.Series:
        """Waste share of the paper industry's biomass and waste per node (Eurostat),
        EU27 where a node has no data, 0 if neither is available."""
        eurostat = cast(Eurostat, self.data["eurostat"])
        share = eurostat.get_paper_waste_share(DATA_YEAR)
        fallback = share.get(EUROSTAT_EU, np.nan)
        fallback = 0.0 if pd.isna(fallback) else float(fallback)
        return share.reindex(list(nodes)).fillna(fallback).rename_axis("node")
