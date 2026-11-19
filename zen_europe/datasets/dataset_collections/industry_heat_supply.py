from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import SourceInformation

from zen_europe.datasets.dataset_collections.ceramic_production_data import (
    CeramicProductionData,
)
from zen_europe.datasets.dataset_collections.food_production_data import (
    FoodProductionData,
)
from zen_europe.datasets.dataset_collections.glass_production_data import (
    GlassProductionData,
)
from zen_europe.datasets.dataset_collections.paper_production_data import (
    PaperProductionData,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.bfe_industry import BFEIndustry
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.jrc_idees import JRCIDEES
from zen_europe.datasets.datasets.technology.stark2025 import Stark2025
from zen_europe.utils.industry import (
    BOILER_FUELS,
    DATA_YEAR,
    HEAT_LEVELS,
    HEAT_SOURCES,
    IDEES_EU,
    NODES_WITHOUT_IDEES,
    SECTORS,
    model_nodes,
    model_sectors,
    sector_fuel,
)
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
    instance_cache,
)

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings

logger = logging.getLogger(__name__)

# production data collection of an industry heat sector
SectorProductionData = (
    GlassProductionData
    | CeramicProductionData
    | PaperProductionData
    | FoodProductionData
)

# boilers with an existing fleet; no existing electrode boilers
COMBUSTION_FUELS = [fuel for fuel in BOILER_FUELS if fuel != "electrode"]
# Eurostat aggregate for nodes without paper biomass and waste data
EUROSTAT_EU = "EU27_2020"
# existing boiler capacities below this value per node (GW) are set to zero, to avoid
# negligible boiler fleets
MIN_BOILER_CAPACITY = 0.005
# capacity limit of the zero-cost pass-through technologies (temperature cascade,
# natural gas kiln fuel) as a multiple of the flat demand they serve, so that the
# optimization does not overbuild them to expand other technologies
CAPACITY_LIMIT_MARGIN = 2.0
# build-out years of the DH heat pump fleet; its annual build-out seeds the unbounded
# capacity addition of the industry heat pumps, see docs, 'Diffusion'
HP_SEED_YEARS = 15
# share of the band demand per node the industry heat pumps are capped at in the
# first optimized year, see docs, 'Diffusion'
HP_SHARE_FIRST_YEAR = 0.02


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
            "glass_production_data": GlassProductionData(
                self.settings, self.source_path
            ),
            "ceramic_production_data": CeramicProductionData(
                self.settings, self.source_path
            ),
            "paper_production_data": PaperProductionData(
                self.settings, self.source_path
            ),
            "food_production_data": FoodProductionData(self.settings, self.source_path),
            "eurostat": Eurostat(self.settings, self.source_path),
            "bfe_industry": BFEIndustry(self.source_path),
            "jrc_idees": JRCIDEES(self.source_path),
            "technology_cost_database": TechnologyCostDatabase(
                self.settings, self.source_path
            ),
            "stark2025": Stark2025(self.source_path),
        }

    # ---------- boilers ----------

    def get_capacity_existing_boiler(self, element: Element) -> Attribute:
        """
        Get the existing capacity of an industrial boiler.

        The heat demand of each industry heat sector is split by the sector's
        JRC-IDEES fuel mix in the node (BFE for CH) and summed over the sectors.
        """
        capacity = (
            self._calculate_boiler_capacity(model_nodes(element))
            .loc[list(model_sectors(element)), element.fuel]
            .groupby(level="node")
            .sum()
        )
        # drop the smallest boilers of a node
        capacity = capacity.where(capacity >= MIN_BOILER_CAPACITY, 0.0)
        data = capacity.to_frame(element.settings.time.reference_year - 1)
        capacity_addition = calculate_capacity_addition_from_cumulative(data, element)
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            df=format_capacity_existing(capacity_addition),
            source=SourceInformation(
                description=(
                    "The existing boiler capacity equals the heat demand (0-200 °C) "
                    "of the industry heat sectors, each split by its JRC-IDEES fuel "
                    "mix in the country (EU27 for NO and UK; BFE industry fuel mix "
                    "for CH). "
                    "'Biomass and waste' is biomass, except in paper, where it is "
                    "split by the Eurostat paper industry final consumption "
                    "(FC_IND_PPP_E). There are no existing electrode boilers. Boilers "
                    f"below {MIN_BOILER_CAPACITY} GW per node are dropped, to avoid "
                    "negligible boiler fleets; the capacity is assumed to be built "
                    "evenly over the lifetime of the technology."
                ),
                metadata=self.metadata,
            ),
        )

    def get_attribute_waste_boiler(self, element: Element, name: str) -> Attribute:
        """Get the attribute `name` of the industrial waste boiler: that of
        waste_boiler_DH, since DEA has no industrial waste boiler."""
        dh_attribute = getattr(
            element.model.conversion_technologies["waste_boiler_DH"], name
        )
        return getattr(element, name).set_data(
            default_value=dh_attribute.default_value,
            unit=dh_attribute.unit,
            df=dh_attribute.df,
            yearly_variations_df=dh_attribute.yearly_variations_df,
            source=SourceInformation(
                description=(
                    "As waste_boiler_DH, since DEA has no industrial waste boiler."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- heat pumps ----------

    def get_capex_specific_conversion_heat_pump_waste_heat(
        self, element: Element
    ) -> Attribute:
        """Get the DEA investment cost of the heat pump plus the waste-heat recovery
        of Stark et al. (2025)."""
        tech_db = cast(TechnologyCostDatabase, self.data["technology_cost_database"])
        capex = tech_db.get_capex_specific_conversion(
            element, proxy_element_name=element.cost_proxy
        )
        price_year = self.settings.time.price_year
        recovery = cast(
            Stark2025, self.data["stark2025"]
        ).get_capex_waste_heat_recovery(price_year)
        return capex.set_data(
            default_value=capex.default_value + recovery,
            df=None if capex.df is None else capex.df + recovery,
            source=SourceInformation(
                description=(
                    f"The DEA investment cost of '{element.cost_proxy}' (Danish Energy "
                    "Agency, Technology Data for Industrial Process Heat, "
                    "https://www.ens.dk/technologydata) plus the waste-heat recovery "
                    "of 1,788 USD/kWth (2025 USD) in Stark et al. (2025), converted "
                    f"to {recovery:.0f} Euro/kW ({price_year} Euro) with the ECB "
                    "dollar-to-euro exchange rate of 2025 and the ECB inflation."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing_heat_pump(self, element: Element) -> Attribute:
        """Get the existing capacity of an industrial heat pump: none today."""
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            source=SourceInformation(
                description="There are no existing industrial heat pumps.",
                metadata=self.metadata,
            ),
        )

    def get_capacity_limit_heat_pump(self, element: Element) -> Attribute:
        """Get the first-year cap (share of band demand) and, for waste heat, the
        industry heat sectors' waste heat in the band."""
        nodes = pd.Index(model_nodes(element), name="node")
        years = pd.Index(self.settings.time.years, name="year")
        sectors = model_sectors(element)
        limit = pd.Series(np.inf, index=nodes)
        description = ""
        if element.heat_source == "waste_heat":
            limit = pd.Series(0.0, index=nodes)
            for sector in sectors:
                production = self._production_data(sector)
                heat = production.calculate_heat_conversion_factors()
                share = heat[element.temp_level] / heat[list(HEAT_LEVELS)].sum()
                fuel = production.calculate_energy_intensity()["fuel"]
                waste_heat = (
                    production.calculate_production(tuple(nodes)) * fuel * share
                )
                limit = limit.add(waste_heat.reindex(nodes, fill_value=0.0))
            description = (
                "Waste heat of the industry heat sectors' processes > 200 °C (their "
                "fuel demand), split by band heat demand. "
            )
        demand = self._calculate_heat_demand(
            sectors, (element.temp_level,), tuple(nodes)
        )
        first_year = (
            demand.reindex(nodes, fill_value=0.0)
            * HP_SHARE_FIRST_YEAR
            / len(HEAT_SOURCES)
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
                    + f"{years[0]}: at most {HP_SHARE_FIRST_YEAR:.0%} of band demand "
                    "per node, since there are no industrial heat pumps today, split "
                    "by heat source, see docs, 'Diffusion'."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_addition_unbounded_heat_pump(self, element: Element) -> Attribute:
        """Get the seed: annual build-out of the existing DH heat pump fleet, split by
        band demand share, heat source and node."""
        heat_pump_dh = element.model.elements["heat_pump_DH"]
        fleet = float(heat_pump_dh.capacity_existing.df.squeeze().sum())
        nodes = model_nodes(element)
        demand = (
            self._calculate_band_demand(nodes)
            .loc[list(model_sectors(element))]
            .sum(axis=1)
        )
        # no seed without industry heat sectors in the model
        band_demand = demand.groupby(level="level").sum().get(element.temp_level, 0.0)
        share = band_demand / demand.sum() if demand.sum() > 0 else 0.0
        heat_sources = len(HEAT_SOURCES)
        interval = self.settings.time.interval_between_years
        return element.capacity_addition_unbounded.set_data(
            default_value=(
                fleet / HP_SEED_YEARS * interval * share / heat_sources / len(nodes)
            ),
            unit="GW",
            source=SourceInformation(
                description=(
                    "Annual build-out of the DH heat pumps (fleet / "
                    f"{HP_SEED_YEARS} yr) per period, split by band demand share, "
                    "heat source and node, see docs, 'Diffusion'."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- temperature cascade ----------

    def get_conversion_factor_temp_conversion(self, element: Element) -> Attribute:
        """Get the lossless downgrade: one unit of heat of the higher band per unit of
        the lower band."""
        higher_band = element.input_carrier.default_value[0]
        return element.conversion_factor.set_data(
            default_value=[{higher_band: {"default_value": 1.0, "unit": "GW/GW"}}],
            source=SourceInformation(
                description="Lossless heat downgrade.",
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing_temp_conversion(self, element: Element) -> Attribute:
        """Get today's heat flow down the cascade: all lower bands are supplied by
        boilers."""
        capacity = self._calculate_heat_demand(
            model_sectors(element), element.served_levels, model_nodes(element)
        )
        data = capacity.to_frame(element.settings.time.reference_year - 1)
        capacity_addition = calculate_capacity_addition_from_cumulative(data, element)
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            df=format_capacity_existing(capacity_addition),
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
            model_sectors(element), element.served_levels, model_nodes(element)
        )
        return self._set_capacity_limit(element, capacity)

    # ---------- thermal energy storage ----------

    def get_capacity_limit_tes(self, element: Element) -> Attribute:
        """Get the heat demand of the storage's band and all lower bands times the
        capacity limit margin, 0 at nodes without demand."""
        levels = HEAT_LEVELS[: HEAT_LEVELS.index(element.temp_level) + 1]
        nodes = model_nodes(element)
        demand = self._calculate_heat_demand(model_sectors(element), levels, nodes)
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
        """Get today's natural gas demand of the sector's kilns or furnaces."""
        capacity = self._production_data(element.sector).calculate_production(
            model_nodes(element)
        ) * self._kiln_fuel_intensity(element)
        data = capacity.to_frame(element.settings.time.reference_year - 1)
        capacity_addition = calculate_capacity_addition_from_cumulative(data, element)
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            df=format_capacity_existing(capacity_addition),
            source=SourceInformation(
                description=(
                    "The existing capacity equals the natural gas demand of today's "
                    "kilns and furnaces."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_limit_kiln_fuel(self, element: Element) -> Attribute:
        """Get today's natural gas demand of the sector's kilns or furnaces times the
        capacity limit margin."""
        demand = self._production_data(element.sector).calculate_demand(
            model_nodes(element)
        ) * self._kiln_fuel_intensity(element)
        return self._set_capacity_limit(element, demand)

    # ---------- helpers ----------

    def _production_data(self, sector: str) -> SectorProductionData:
        """Production data collection of the industry heat sector `sector`."""
        return cast(SectorProductionData, self.data[f"{sector}_production_data"])

    def _set_capacity_limit(
        self,
        element: Element,
        demand: pd.Series,
        description: str = "The flat demand",
        nodes: tuple[str, ...] | None = None,
    ) -> Attribute:
        """Limit a technology to the demand times the capacity limit margin, see
        docs, 'Diffusion'. With `nodes`, the limit is 0 at nodes without demand."""
        limit = demand * CAPACITY_LIMIT_MARGIN
        description = (
            f"{description} times the capacity limit margin of "
            f"{CAPACITY_LIMIT_MARGIN}, see docs, 'Diffusion'."
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
        return self._production_data(element.sector).calculate_conversion_factors()[
            sector_fuel(element.sector)
        ]

    def _calculate_heat_demand(
        self, sectors: tuple[str, ...], levels: tuple[str, ...], nodes: tuple[str, ...]
    ) -> pd.Series:
        """Heat demand (GW) of the sectors' products in the given bands."""
        demand = self._calculate_band_demand(nodes)
        selected = demand.index.get_level_values("sector").isin(
            sectors
        ) & demand.index.get_level_values("level").isin(levels)
        return demand[selected].sum()

    @instance_cache
    def _calculate_band_demand(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Heat demand (GW) per sector and band (rows) and node (columns)."""
        demand = {
            (sector, level): self._production_data(sector).calculate_demand(nodes)
            * heat
            for sector in SECTORS
            for level, heat in self._production_data(sector)
            .calculate_heat_conversion_factors()
            .items()
        }
        return pd.DataFrame(demand).T.rename_axis(["sector", "level"])

    @instance_cache
    def _calculate_boiler_capacity(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Boiler capacity (GW) per sector and node (rows) and fuel (columns): the
        sector's heat demand split by its fuel mix."""
        # product demand basis, as the heat carriers
        demand = pd.concat(
            {
                sector: self._production_data(sector).calculate_demand(nodes)
                * self._production_data(sector).calculate_energy_intensity()["heat"]
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
