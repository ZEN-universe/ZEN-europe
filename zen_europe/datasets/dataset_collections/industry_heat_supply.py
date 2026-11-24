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
from zen_europe.datasets.dataset_collections.heat_demand import HeatDemand
from zen_europe.datasets.dataset_collections.industry_production_data import (
    DATA_YEAR,
)
from zen_europe.datasets.dataset_collections.paper_production_data import (
    PaperProductionData,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.bfe_industry import BFEIndustry
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.jrc_idees import (
    IDEES_EU,
    JRCIDEES,
    NODES_WITHOUT_IDEES,
)
from zen_europe.datasets.datasets.technology.bever2024 import Bever2024
from zen_europe.datasets.datasets.technology.stark2025 import Stark2025
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    class_attribute,
    conversion_entries,
    format_capacity_existing,
    instance_cache,
)

if TYPE_CHECKING:
    from zen_creator import ConversionTechnology, Dataset
    from zen_creator.utils.settings import Settings

logger = logging.getLogger(__name__)

# industry heat sectors and the heat sources and boiler fuels supplying them, see
# docs, "Industry heat sectors"
SECTORS = ("glass", "ceramic", "paper", "food")
HEAT_SOURCES = ("waste_heat", "water")
BOILER_FUELS = ("biomass", "natural_gas", "electrode", "oil", "coal", "waste")
# production data collection of an industry heat sector
SectorProductionData = (
    GlassProductionData
    | CeramicProductionData
    | PaperProductionData
    | FoodProductionData
)

# boilers with an existing fleet; no existing electrode boilers
COMBUSTION_FUELS = [fuel for fuel in BOILER_FUELS if fuel != "electrode"]
# existing boiler capacities below this value per node (GW) are set to zero, to avoid
# negligible boiler fleets
MIN_BOILER_CAPACITY = 0.005
# capacity limit of the zero-cost pass-through technologies (temperature cascade,
# natural gas kiln fuel) as a multiple of the flat demand they serve, so that the
# optimization does not overbuild them to expand other technologies. The lower level
# of the temperature cascade is limited to 8 times the demand, since the there are
# endogenous demands (e.g., DAC) in the lower bands,
# while the upper level only has the flat demand. All other technologies are limited
# to CAPACITY_LIMIT_DEFAULT times the flat demand, to avoid overbuilding them to expand
# other technologies. See docs, 'Diffusion'.
CAPACITY_LIMIT_MARGIN = {
    "heat_industry_temp_conversion_100": 8,
    "heat_industry_temp_conversion_150": 2,
}
CAPACITY_LIMIT_DEFAULT = 2
# TODO required?
# build-out years of the DH heat pump fleet; its annual build-out seeds the unbounded
# capacity addition of the industry heat pumps, see docs, 'Diffusion'
HP_SEED_YEARS = 15


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
            "bever2024": Bever2024(self.source_path),
        }

    # ---------- boilers ----------

    def get_capacity_existing_boiler(self, element: ConversionTechnology) -> Attribute:
        """
        Get the existing capacity of an industrial boiler.

        The heat demand of each industry heat sector is split by the sector's
        JRC-IDEES fuel mix in the node (BFE for CH) and summed over the sectors.
        """
        boilers = self._select_model_sectors(
            element,
            self._calculate_boiler_capacity(
                tuple(element.model.config.system.set_nodes)
            ),
        )
        capacity = boilers[class_attribute(element, "fuel")].groupby(level="node").sum()
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

    def get_attribute_waste_boiler(
        self, element: ConversionTechnology, name: str
    ) -> Attribute:
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

    def get_conversion_factor_heat_pump_waste_heat(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the electricity per heat of Bever et al. (2024) plus the recoverable
        waste heat per heat: the rest of the heat output, 1 - 1/COP."""
        attr = cast(Bever2024, self.data["bever2024"]).get_conversion_factor_heat_pump(
            element
        )
        share = self._waste_heat_share_heat_pump(element)
        entry = {"default_value": round(share, 12), "unit": "GW/GW"}
        return attr.set_data(
            default_value=[
                *conversion_entries(attr),
                {"recoverable_waste_heat": entry},
            ],
            source=SourceInformation(
                description=(
                    "The heat pump takes the heat output not supplied by electricity "
                    f"from the recoverable waste heat: 1 - 1/COP = {share:.3f}."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capex_specific_conversion_heat_pump_waste_heat(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the DEA investment cost of the heat pump plus the waste-heat recovery
        of Stark et al. (2025) per recovered waste heat."""
        tech_db = cast(TechnologyCostDatabase, self.data["technology_cost_database"])
        cost_proxy = class_attribute(element, "cost_proxy")
        capex = tech_db.get_capex_specific_conversion(
            element, proxy_element_name=cost_proxy
        )
        price_year = self.settings.time.price_year
        recovery = cast(
            Stark2025, self.data["stark2025"]
        ).get_capex_waste_heat_recovery(price_year)
        share = self._waste_heat_share_heat_pump(element)
        recovery_per_output = recovery * share
        return capex.set_data(
            default_value=cast(float, capex.default_value) + recovery_per_output,
            df=None if capex.df is None else capex.df + recovery_per_output,
            source=SourceInformation(
                description=(
                    f"The DEA investment cost of '{cost_proxy}' (Danish Energy "
                    "Agency, Technology Data for Industrial Process Heat, "
                    "https://www.ens.dk/technologydata) plus the waste-heat recovery "
                    "of 1,788 USD/kWth (2025 USD) in Stark et al. (2025), converted "
                    f"to {recovery:.0f} Euro/kW ({price_year} Euro) with the ECB "
                    "dollar-to-euro exchange rate of 2025 and the ECB inflation. The "
                    "recovery cost is per kW of recovered waste heat, so it is "
                    f"multiplied by the waste heat per heat output, 1 - 1/COP = "
                    f"{share:.3f}, giving {recovery_per_output:.0f} Euro/kW of heat."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing_heat_pump(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the existing capacity of an industrial heat pump: none today."""
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            source=SourceInformation(
                description="There are no existing industrial heat pumps.",
                metadata=self.metadata,
            ),
        )

    def get_capacity_addition_unbounded_heat_pump(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the seed: annual build-out of today's DH heat pump fleet, split by
        band demand share, heat source and node."""
        fleet = self._calculate_dh_heat_pump_fleet(
            element.model.conversion_technologies["heat_pump_DH"]
        )
        nodes = tuple(element.model.config.system.set_nodes)
        demand = self._select_model_sectors(
            element, self._calculate_band_demand(nodes)
        ).sum(axis=1)
        # no seed without industry heat sectors in the model
        band_demand = (
            demand.groupby(level="level")
            .sum()
            .get(class_attribute(element, "temp_level"), 0.0)
        )
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

    def get_conversion_factor_temp_conversion(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the lossless downgrade: one unit of heat of the higher band per unit of
        the lower band."""
        higher_band = cast(list[str], element.input_carrier.default_value)[0]
        return element.conversion_factor.set_data(
            default_value=[{higher_band: {"default_value": 1.0, "unit": "GW/GW"}}],
            source=SourceInformation(
                description="Lossless heat downgrade.",
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing_temp_conversion(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get today's heat flow down the cascade: all lower bands are supplied by
        boilers."""
        capacity = self._calculate_heat_demand(
            element, class_attribute(element, "served_levels")
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

    def get_capacity_limit_temp_conversion(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the heat demand of the lower bands times the capacity limit margin."""
        capacity = self._calculate_heat_demand(
            element, class_attribute(element, "served_levels")
        )
        return self._set_capacity_limit(element, capacity)

    # ---------- thermal energy storage ----------

    # ---------- kiln fuel ----------

    def get_capacity_existing_kiln_fuel(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get today's natural gas demand of the sector's kilns or furnaces."""
        capacity = self._production_data(
            class_attribute(element, "sector")
        ).calculate_production(
            tuple(element.model.config.system.set_nodes)
        ) * self._kiln_fuel_intensity(
            element
        )
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

    def get_capacity_limit_kiln_fuel(self, element: ConversionTechnology) -> Attribute:
        """Get today's natural gas demand of the sector's kilns or furnaces times the
        capacity limit margin."""
        demand = self._production_data(
            class_attribute(element, "sector")
        ).calculate_demand(
            tuple(element.model.config.system.set_nodes)
        ) * self._kiln_fuel_intensity(
            element
        )
        return self._set_capacity_limit(element, demand)

    # ---------- helpers ----------

    def _production_data(self, sector: str) -> SectorProductionData:
        """Production data collection of the industry heat sector `sector`."""
        return cast(SectorProductionData, self.data[f"{sector}_production_data"])

    def _waste_heat_share_heat_pump(self, element: ConversionTechnology) -> float:
        """Recoverable waste heat per heat output of a waste-heat heat pump:
        1 - 1/COP."""
        cop = cast(Bever2024, self.data["bever2024"]).get_cop(
            class_attribute(element, "temp_level"),
            class_attribute(element, "heat_source"),
        )
        return 1.0 - 1.0 / cop

    def _set_capacity_limit(
        self,
        element: ConversionTechnology,
        demand: pd.Series,
        description: str = "The flat demand",
        nodes: tuple[str, ...] | None = None,
    ) -> Attribute:
        """Limit a technology to the demand times the capacity limit margin, see
        docs, 'Diffusion'. With `nodes`, the limit is 0 at nodes without demand."""
        capacity_limit_margin = CAPACITY_LIMIT_MARGIN.get(
            element.name, CAPACITY_LIMIT_DEFAULT
        )
        limit = demand * capacity_limit_margin
        description = (
            f"{description} times the capacity limit margin of "
            f"{capacity_limit_margin}, see docs, 'Diffusion'."
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

    def _kiln_fuel_intensity(self, element: ConversionTechnology) -> float:
        sector = class_attribute(element, "sector")
        return self._production_data(sector).calculate_conversion_factors()[
            f"{sector}_fuel"
        ]

    @staticmethod
    def _select_model_sectors(
        element: ConversionTechnology, data: pd.DataFrame
    ) -> pd.DataFrame:
        """Rows of `data` of the industry heat sectors in the element's model."""
        sectors = data.index.get_level_values("sector")
        return data[sectors.isin(list(element.model.sectors))]

    def _calculate_heat_demand(
        self, element: ConversionTechnology, levels: tuple[str, ...]
    ) -> pd.Series:
        """Heat demand (GW) of the model's industry heat sectors in the given
        bands."""
        demand = self._select_model_sectors(
            element,
            self._calculate_band_demand(tuple(element.model.config.system.set_nodes)),
        )
        return demand[demand.index.get_level_values("level").isin(levels)].sum()

    @instance_cache
    def _calculate_dh_heat_pump_fleet(
        self, heat_pump_dh: ConversionTechnology
    ) -> float:
        """Today's DH heat pump fleet (GW), also when existing capacities are not
        used, so that the seed does not depend on that setting."""
        heat_demand = HeatDemand(self.settings, cast(Path, self.source_path))
        fleet = heat_demand.calculate_capacity_existing(heat_pump_dh, is_dh=True)
        return float(fleet.sum())

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
        sector_shares = {}
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
            sector_shares[sector] = fuels.fillna(0.0)
        shares = pd.concat(sector_shares, names=["sector", "node"])
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
        fallback = share.get("EU27_2020", np.nan)
        fallback = 0.0 if pd.isna(fallback) else float(fallback)
        return share.reindex(list(nodes)).fillna(fallback).rename_axis("node")
