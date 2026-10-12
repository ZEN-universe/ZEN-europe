from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.datasets.datasets.carrier.entsoe import ENTSOE
from zen_europe.datasets.datasets.technology.iosn_candidate_units import (
    IoSNCandidateUnits,
)
from zen_europe.datasets.datasets.technology.tyndp_electricity_results import (
    TYNDPElectricityModellingResults,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import Attribute, DatasetCollection, TransportTechnology
from zen_creator.datasets.datasets.metadata import MetadataTree
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings


class PowerLineCapacityLimit(DatasetCollection):
    """Capacity limit of the power lines of the model.

    The limit is the capacity that the European network can reach on an edge,
    either the export capacity that the TYNDP 2022 scenarios model for 2050,
    or the existing capacity plus the capacity increase of all investment
    candidates of the system needs study, or the larger of the two.
    settings.data_source.potential_capacity_power_line selects which one.

    A candidate increases the capacity of a border in both directions, so the
    two directions of an edge get the larger of their values.
    """

    name = "power_line_capacity_limit"

    TYNDP = "tyndp"
    CANDIDATES = "candidates"
    BOTH = "both"

    def __init__(
        self, settings: Settings, source_path: Path | str, set_nodes: list[str]
    ):
        self.settings = settings
        self.set_nodes = set_nodes
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "tyndp_electricity_modelling_results": TYNDPElectricityModellingResults(
                source_path=self.source_path
            ),
            "iosn_candidate_units": IoSNCandidateUnits(source_path=self.source_path),
            "entsoe": ENTSOE(
                settings=self.settings,
                set_nodes=self.set_nodes,
                source_path=self.source_path,
            ),
        }

    # -------- outward-facing accessors ------------------
    def get_capacity_limit(self, technology: TransportTechnology) -> Attribute:
        """Get the capacity limit of the power lines of every edge."""
        potential = self.settings.data_source.potential_capacity_power_line
        set_edges = technology.model.energy_system.set_edges.df
        if set_edges is None:
            raise ValueError(
                "The capacity limit cannot be determined, because the energy "
                "system of the model defines no edges."
            )

        limits = {}
        metadata: Dict[str, MetadataTree] = {}
        if potential in (self.TYNDP, self.BOTH):
            limits[self.TYNDP] = self._get_limit_tyndp(set_edges)
            metadata["tyndp_electricity_modelling_results"] = self.data[
                "tyndp_electricity_modelling_results"
            ].metadata
        if potential in (self.CANDIDATES, self.BOTH):
            limits[self.CANDIDATES] = self._get_limit_candidates(set_edges)
            metadata["iosn_candidate_units"] = self.data[
                "iosn_candidate_units"
            ].metadata
            metadata["entsoe"] = self.data["entsoe"].metadata
        if not limits:
            raise ValueError(
                f"'{potential}' is not a known source of the power line "
                f"capacity limit in the dataset collection '{self.name}'."
            )

        capacity_limit = pd.DataFrame(limits).max(axis=1)
        capacity_limit.name = "capacity_limit"
        capacity_limit.index.name = "edge"
        attr = technology.capacity_limit
        return attr.set_data(
            default_value=0,
            df=capacity_limit,
            unit="GW",
            source=SourceInformation(
                description=self._get_description(potential),
                metadata=(
                    metadata if len(metadata) > 1 else next(iter(metadata.values()))
                ),
            ),
        )

    # -------- capacity limit internals ------------------
    def _get_limit_tyndp(self, set_edges: pd.DataFrame) -> pd.Series:
        """The export capacity that the TYNDP 2022 scenarios model per edge."""
        modelling_results = cast(
            TYNDPElectricityModellingResults,
            self.data["tyndp_electricity_modelling_results"],
        )
        capacity = modelling_results.get_export_capacity(self.set_nodes)
        return self._to_edges(self._symmetric(capacity), set_edges)

    def _get_limit_candidates(self, set_edges: pd.DataFrame) -> pd.Series:
        """The existing capacity plus the increase of all candidates per edge."""
        candidate_units = cast(IoSNCandidateUnits, self.data["iosn_candidate_units"])
        increase = candidate_units.get_capacity_increase(self.set_nodes)
        increase = self._to_edges(self._symmetric(increase), set_edges)

        entsoe = cast(ENTSOE, self.data["entsoe"])
        capacity_existing = entsoe.get_transmission_capacity()
        capacity_existing = capacity_existing["capacity_existing"].droplevel(
            "year_construction"
        )
        capacity_existing = (
            capacity_existing.groupby("edge").sum().reindex(set_edges.index).fillna(0.0)
        )
        return capacity_existing + increase

    def _to_edges(self, capacity: pd.Series, set_edges: pd.DataFrame) -> pd.Series:
        """Map a capacity per country pair onto the edges of the model."""
        pairs = pd.MultiIndex.from_frame(set_edges[["node_from", "node_to"]])
        capacity = capacity.reindex(pairs).fillna(0.0)
        capacity.index = set_edges.index
        return capacity

    @staticmethod
    def _symmetric(capacity: pd.Series) -> pd.Series:
        """Give both directions of a country pair the larger of their values."""
        reverse = capacity.copy()
        reverse.index = pd.MultiIndex.from_tuples(
            [(node_to, node_from) for node_from, node_to in capacity.index],
            names=capacity.index.names,
        )
        return pd.concat([capacity, reverse], axis=1).max(axis=1)

    def _get_description(self, potential: str) -> str:
        """The description of the capacity limit of the selected source."""
        tyndp = (
            "the export capacity that the TYNDP 2022 scenarios model for the "
            "year 2050"
        )
        candidates = (
            "the existing net transfer capacity of the ENTSO-E Transparency "
            "Platform plus the capacity increase of all investment candidates "
            "of the TYNDP 2022 system needs study"
        )
        if potential == self.TYNDP:
            source = tyndp
        elif potential == self.CANDIDATES:
            source = candidates
        else:
            source = f"the larger of {tyndp} and {candidates}"
        return (
            f"The capacity limit of the power lines is {source}. Both "
            f"directions of an edge get the larger of their values, and an "
            f"edge that is not reported cannot be expanded."
        )
