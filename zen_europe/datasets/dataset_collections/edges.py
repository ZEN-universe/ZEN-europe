from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Element, TransportTechnology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.energy_system.nuts_shp import NUTSshp
from zen_europe.datasets.datasets.energy_system.tyndp_edges import TYNDP_2020_edges


class Edges(DatasetCollection):
    """For creating edges in ZEN-garden."""

    name = "edges"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "nuts_shp": NUTSshp(self.source_path),
            "tyndp_2020_edges": TYNDP_2020_edges(self.source_path),
        }

    def get_set_edges(self, element: Element) -> Attribute:
        """
        Creates edges.

        Nuts_edges uses adjacency of different NUTS regions to set edges.
        TYNDP_edges uses existing data from TYNDP to set edges.
        This function takes the union of both edge types.
        """

        nuts_dataset = cast(NUTSshp, self.data["nuts_shp"])
        tyndp_dataset = cast(TYNDP_2020_edges, self.data["tyndp_2020_edges"])

        nuts_edges = nuts_dataset.get_set_edges(element).df
        tyndp_edges = tyndp_dataset.get_set_edges(element).df

        set_edges = pd.concat([nuts_edges, tyndp_edges]).drop_duplicates().sort_index()

        # Create edges
        attr = element.set_edges
        return attr.set_data(
            default_value=None,
            df=set_edges,
            source=SourceInformation(
                description=(
                    "Edges are constructed in two steps: first, NUTS0 "
                    "countries that share a border are assumed to be "
                    "connected by an edge [NUTSshp]; "
                    "second, transmission edges from "
                    "TYNDP are added to this adjacency-based network."
                    "[tyndp_2020_edges]"
                ),
                metadata=self.metadata,
            ),
        )

    def get_edges_offshore(self, element: Element, set_nodes: list[str]) -> pd.Index:
        """
        Gets the edges of the energy system that cross the sea.

        Edges are created both between countries that share a border and
        between countries that are connected by transmission infrastructure, so
        the edges that are not an adjacency edge of set_nodes are the ones that
        do not connect two adjacent countries.
        """
        set_edges = element.model.energy_system.set_edges.df
        if set_edges is None:
            raise ValueError(
                "The offshore edges cannot be determined, because the energy "
                "system of the model defines no edges."
            )
        nuts_dataset = cast(NUTSshp, self.data["nuts_shp"])
        edges_adjacent = nuts_dataset.get_set_edges_adjacent(set_nodes)
        edges_offshore = set_edges.index.difference(edges_adjacent.index)
        edges_offshore.name = "edge"
        return edges_offshore

    def get_capacity_limit_offshore(self, element: TransportTechnology) -> Attribute:
        """
        Gets the capacity limit of a transport technology that cannot be built
        offshore.

        The capacity limit is 0 on the edges that cross the sea, while the
        default value of the attribute applies on all other edges.
        """
        edges_offshore = self.get_edges_offshore(
            element, element.model.config.system.set_nodes
        )
        attr = element.capacity_limit
        if edges_offshore.empty:
            return attr
        capacity_limit = pd.Series(
            data=0.0, index=edges_offshore, name="capacity_limit"
        )
        return attr.set_data(
            df=capacity_limit,
            source=SourceInformation(
                description=(
                    f"{element.name} cannot be built on the edges that do not "
                    f"connect two adjacent countries, so its capacity limit is "
                    f"0 on those {len(edges_offshore)} edges."
                ),
                metadata=self.metadata,
            ),
        )
