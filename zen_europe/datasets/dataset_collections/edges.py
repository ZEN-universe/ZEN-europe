from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.datasets.datasets.dataset import Dataset
    from zen_creator.elements.element import Element


from zen_creator.datasets.datasets.nuts_shp import NUTSshp
from zen_creator.datasets.datasets.tyndp_edges import TYNDP_2020_edges

from zen_creator.datasets.dataset_collections.dataset_collection import (
    DatasetCollection,
)
from zen_creator.utils.attribute import Attribute


class Edges(DatasetCollection):
    """For creating edges in ZEN-garden."""

    name = "edges"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset]:
        """Load all available data sources."""

        return {
            "NUTSshp": NUTSshp(self.source_path),
            "TYNDP_2020_edges": TYNDP_2020_edges(self.source_path),
        }

    def get_set_edges(self, element: Element) -> Attribute:
        """
        Creates edges.

        Nuts_edges uses adjacency of different NUTS regions to set edges.
        TYNDP_edges uses existing data from TYNDP to set edges.
        This function takes the union of both edge types.
        """

        nuts_edges = self.data["NUTSshp"].get_set_edges(element).df
        tyndp_edges = self.data["TYNDP_2020_edges"].get_set_edges(element).df

        set_edges = pd.concat([nuts_edges, tyndp_edges]).drop_duplicates().sort_index()

        # Create edges
        attr = Attribute(
            name="set_edges",
            default_value=None,
            element=element,
            df=set_edges,
            source=self.metadata,
        )

        return attr
