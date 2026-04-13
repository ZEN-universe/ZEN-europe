from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import geopandas as gpd
import numpy as np
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_creator.elements.element import Element


class NUTSshp(Dataset[pd.DataFrame]):
    name = "nuts_shp"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _set_title(self) -> str:
        return "Territorial units for statistics (NUTS)"

    def _set_author(self) -> str:
        return "Eurostat"

    def _set_publication(self) -> str:
        return "Eurostat"

    def _set_publication_year(self) -> int:
        return 2026

    def _set_url(self) -> str:
        return "https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics"

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "01-energy_system" / "nodes_edges"

    def _set_data(self) -> pd.DataFrame:
        gdf = gpd.read_file(self.path / "NUTS_RG_60M_2021_3035.shp")
        return gdf

    # -------- methods ------------------------

    def get_set_edges(self, element: Element) -> Attribute:
        """
        Creates edges between adjacent NUTS regions.

        There is an edge between any two regions that are touching.

        Returns:
            Attribute: Attribute with no default value and the edges
                listed as data.
        """
        # filter GeoDataFrame
        nodes = element.model.config.system.set_nodes
        data = cast(gpd.GeoDataFrame, self.data)
        regions = data[data["NUTS_ID"].isin(nodes)]

        # build connectivity matrix
        connectivity_matrix = pd.DataFrame(
            index=nodes, columns=nodes, data=0, dtype=int
        )
        for _index, row in regions.iterrows():
            neighbors = regions[regions.geometry.touches(row["geometry"])]["NUTS_ID"]
            connectivity_matrix.loc[row["NUTS_ID"], neighbors] = 1

        # reformat connectivity_matrix
        connectivity_series = cast(pd.Series, connectivity_matrix.stack())
        nodes_in_edges = connectivity_series[connectivity_series == 1].to_frame()
        nodes_in_edges["edge"] = [
            f"{node_from}-{node_to}" for node_from, node_to in nodes_in_edges.index
        ]
        nodes_in_edges.index.names = ["node_from", "node_to"]
        set_edges = nodes_in_edges.drop(columns=0)
        set_edges = set_edges.reset_index().set_index("edge")

        # create attribute
        attr = Attribute(
            "set_edges",
            element=element,
            default_value=[],
            df=set_edges,
            source=self.metadata,
        )

        return attr

    def get_set_nodes(self, element: Element) -> Attribute:
        """
        Extract the centroid of all nodes specified in the config.

        Nodes must be NUTS regions for the extraction process to work.

        Returns:

            Attribute: Attribute with no default value and the node
                coordinates listed as data.

        """
        # get nodes
        nodes = np.array(element.model.config.system.set_nodes)

        # check that all nodes are NUTS regions
        if not np.all(np.isin(nodes, self.data["NUTS_ID"])):
            missing_nodes = nodes[~np.isin(nodes, self.data["NUTS_ID"])]
            raise AssertionError(
                "Invalid nodes. The following nodes "
                "are not valid NUTS regions and can therefore not be "
                f"found in the data: {missing_nodes}"
            )

        # filter GeoDataFrame
        data = cast(gpd.GeoDataFrame, self.data)
        regions = cast(
            gpd.GeoDataFrame, data[data["NUTS_ID"].isin(nodes)].set_index("NUTS_ID")
        )

        # compute centroids and convert coordinates to longitude, latitude
        centroids = regions.geometry.centroid
        centroids = centroids.to_crs(epsg=4326)  # project to WGS84
        centroids.index.name = "node"

        set_nodes = pd.DataFrame(
            {"lon": centroids.x, "lat": centroids.y}, index=centroids.index
        )

        attr = Attribute(
            "set_nodes",
            element=element,
            default_value=None,
            df=set_nodes,
            source=self.metadata,
        )

        return attr
