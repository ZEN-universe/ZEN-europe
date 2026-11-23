from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Carrier, Dataset


from zen_creator import Attribute, ConversionTechnology, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.carrier.manual_steel_demand import (
    Eurofer,
    GlobalIronSteelTracker,
    TradeEconomics,
    WorldSteelInFigures2025,
)
from zen_europe.datasets.datasets.carrier.material_economics import MaterialEconomics
from zen_europe.utils.constants import Constants


class SteelDemand(DatasetCollection):
    """Extracting steel demand data."""

    name = "steel_demand"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "eurofer": Eurofer(self.source_path),
            "worldsteel_2025": WorldSteelInFigures2025(self.source_path),
            "global_iron_steel_tracker": GlobalIronSteelTracker(self.source_path),
            "trade_economics": TradeEconomics(self.source_path),
            "material_economics": MaterialEconomics(self.source_path),
        }

    def _calculate_steel_demand(
        self, element: Carrier
    ) -> tuple[pd.Series, pd.DataFrame]:
        """
        Calculate the steel production per node and the share of the element's route
        per node and year.

        The production is the 2020-2024 mean of Eurofer; nodes missing there take the
        2024 worldsteel production (PT, UK), NO and CH the manual values. The secondary
        share starts at the 2024 electric arc furnace share of each node. 
        We assume that in 2050, every node reaches at least the 60% secondary share 
        of Material Economics. This raises the total secondary share of all nodes
        above the Material Economics share.
        Another approach would be that every node
        closes the same fraction of its gap to a full secondary share, so that the
        secondary share of all nodes together ends at the Material Economics end share.
        Revisit once scrap is implemented.
        """
        eurofer = cast(Eurofer, self.data["eurofer"])
        worldsteel = cast(WorldSteelInFigures2025, self.data["worldsteel_2025"])
        tracker = cast(GlobalIronSteelTracker, self.data["global_iron_steel_tracker"])
        trade_economics = cast(TradeEconomics, self.data["trade_economics"])
        material_economics = cast(MaterialEconomics, self.data["material_economics"])
        nodes = pd.Index(element.model.config.system.set_nodes, name="node")

        production = eurofer.get_crude_steel_output().combine_first(
            worldsteel.get_crude_steel_production()
        )
        production["NO"] = trade_economics.get_manual_steel_demand_trade_economics("NO")
        production["CH"] = eurofer.get_manual_steel_demand_eurofer("CH")
        # worldsteel lists every EU producer, so the other nodes produce no steel
        production = (
            production.reindex(nodes, fill_value=0.0) 
            * 1000 / Constants.HOURS_PER_YEAR)  # Mt/a -> kt/h

        share_start = (
            worldsteel.get_secondary_steel_share()
            .combine_first(tracker.get_secondary_steel_share())
            .reindex(nodes, fill_value=1.0)
        )
        _, share_end_total = material_economics.get_secondary_steel_ratios()
        share_end = share_start.clip(lower=share_end_total)
        years = element.settings.time.years
        share = pd.DataFrame({years[0]: share_start, years[-1]: share_end})
        share = share.reindex(columns=years).interpolate(method="index", axis=1)
        if element.name == "primary_steel":
            share = 1 - share
        share.columns.name = "year"
        return production, share

    def get_steel_demand(self, element: Carrier) -> Attribute:
        """
        Get the demand for steel.

        This function retrieves the steel demand data for the specified element.
        """
        production, share = self._calculate_steel_demand(element)
        yearly_variation = cast(pd.Series, share.stack())
        yearly_variation.name = "demand_yearly_variation"
        source = SourceInformation(
            description=(
                "The steel demand is the crude steel production per node (Eurofer "
                "2020-2024 mean; worldsteel 2024 for PT and UK; TradeEconomics for NO "
                "and Eurofer EU exports for CH), given as the default demand, times "
                "the yearly share of the route as the yearly variation. The secondary "
                "share starts at the 2024 electric arc furnace share per node "
                "(worldsteel; Global Iron and Steel Tracker for CH and NO); every "
                "node closes the same fraction of its gap to a full secondary share "
                "so that all nodes together reach the Material Economics end share."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=production.to_frame("demand"),
            yearly_variations_df=yearly_variation,
            unit="tproduct/h",
        )

    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """
        Get the existing capacity for steel production technologies.

        This function retrieves the existing capacity data for the specified element.
        """
        ref_carrier = cast(list[str], element.reference_carrier.default_value)[0]
        if ref_carrier == "secondary_steel":
            assert element.name == "EAF", (
                "The existing capacity for secondary steel production is assumed"
                "to be exclusive the EAF technology."
            )
        elif ref_carrier == "primary_steel":
            assert element.name == "BF_BOF", (
                "The existing capacity for primary steel production is assumed"
                "to be exclusive the BF-BOF technology."
            )
        else:
            raise ValueError(
                f"Unexpected reference carrier '{ref_carrier}' for element "
                f"'{element.name}'."
            )
        production, share = self._calculate_steel_demand(
            element.model.carriers[ref_carrier]
        )
        steel_demand = (production * share.iloc[:, 0]).to_frame(
            element.settings.time.reference_year - 1
        )
        capacity_addition = calculate_capacity_addition_from_cumulative(
            steel_demand, element
        )
        capacity_existing = format_capacity_existing(capacity_addition)
        source = SourceInformation(
            description=(
                "It is assumed that all current primary steel demand is based on the "
                "BF-BOF route, and all current secondary steel demand is based on the "
                "EAF route. The current steel demand is the crude steel production "
                "per node (Eurofer, worldsteel, TradeEconomics) times its 2024 oxygen "
                "or electric arc furnace share (worldsteel, Global Iron and Steel "
                "Tracker)."
            ),
            metadata=self.metadata,
        )
        return element.capacity_existing.set_data(
            source=source,
            df=capacity_existing,
            unit="tproduct/h",
        )
