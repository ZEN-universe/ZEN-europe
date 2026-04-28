from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Element


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
        attr = Attribute(
            name="set_edges",
            default_value=None,
            element=element,
            df=set_edges,
            sources=[
                SourceInformation(
                    description=(
                        "Edges are constructed in two steps: first, NUTS0 "
                        "countries that share a border are assumed to be "
                        "connected by an edge [NUTSshp]; "
                        "second, transmission edges from "
                        "TYNDP are added to this adjacency-based network."
                        "[tyndp_2020_edges]"
                    ),
                    metadata=self.metadata,
                )
            ],
        )

        return attr
