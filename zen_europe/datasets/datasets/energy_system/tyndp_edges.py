from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.elements.element import Element
from zen_creator.utils.attribute import Attribute


class TYNDP_2020_edges(Dataset[Dict[str, pd.DataFrame]]):
    name = "tyndp_2020_edges"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _set_title(self) -> str:
        return "TYNDP 2020 transmission edges"

    def _set_author(self) -> str:
        return "Jane Doe"

    def _set_publication(self) -> str:
        return "ENTSO-E"

    def _set_publication_year(self) -> int:
        return 2026

    def _set_url(self) -> str:
        return "https://example.com/dataset.csv"

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "01-energy_system" / "nodes_edges"

    def _set_data(self) -> Dict[str, pd.DataFrame]:
        # nodes from ENTSOE TYNDP 2020-scenario.xlsx
        # load nodes and edges
        nodes = pd.read_csv(
            self.path / "Nodes_Dict.csv",
            delimiter=";",
        )
        edges = pd.read_csv(
            self.path / "Lines_Dict.csv",
            delimiter=";",
        )

        return {"nodes": nodes, "edges": edges}

    def get_set_edges(self, element: Element) -> Attribute:

        # get list of nodes used in the model
        set_nodes = np.array(element.model.config.system.set_nodes)

        # load data
        edges = self.data["edges"]
        nodes = self.data["nodes"]

        # filter data
        edges = edges[~edges["line_id"].str.contains("Exp")]

        # create storage
        set_edges = pd.DataFrame(columns=["node_from", "node_to"])

        # iterate through nodes to find corresponding edges
        set_nodes[set_nodes == "EL"] = "GR"
        for node in set_nodes:
            node_ids = nodes["node_id"][nodes["country"] == node].reset_index(drop=True)
            connected_node_id_from_node = []
            connected_node_id_to_node = []
            for node_id in node_ids:
                connected_node_id_from_node.extend(
                    list(edges["node_b"][(edges["node_a"] == node_id)])
                )
                connected_node_id_to_node.extend(
                    list(edges["node_a"][(edges["node_b"] == node_id)])
                )
            # append to set_edges
            set_edges_temp_from_node = pd.DataFrame(columns=["node_from", "node_to"])
            connected_node_from_node = nodes["country"][
                nodes["node_id"].isin(connected_node_id_from_node)
            ]
            # only nodes which are in self.set_nodes
            set_edges_temp_from_node["node_to"] = connected_node_from_node[
                connected_node_from_node.isin(set_nodes)
            ]
            set_edges_temp_from_node["node_from"] = node
            set_edges_temp_to_node = pd.DataFrame(columns=["node_from", "node_to"])
            connected_node_to_node = nodes["country"][
                nodes["node_id"].isin(connected_node_id_to_node)
            ]
            # only nodes which are in self.set_nodes
            set_edges_temp_to_node["node_from"] = connected_node_to_node[
                connected_node_to_node.isin(set_nodes)
            ]
            set_edges_temp_to_node["node_to"] = node
            set_edges = pd.concat(
                [set_edges, set_edges_temp_from_node, set_edges_temp_to_node]
            )
        # remove edges where node_from = node_to
        set_edges = set_edges[set_edges["node_from"] != set_edges["node_to"]]

        # flip direction of edge
        set_edges_flipped = set_edges.rename(
            columns={"node_from": "node_to", "node_to": "node_from"}
        )
        set_edges = pd.concat([set_edges, set_edges_flipped]).drop_duplicates()

        # substitute greece
        set_edges[set_edges == "GR"] = "EL"

        # set edge name
        set_edges["edge"] = set_edges.apply(
            lambda row: row["node_from"] + "-" + row["node_to"], axis=1
        )
        set_edges = set_edges.set_index("edge")

        # Create attribute
        attr = Attribute(
            name="set_edges",
            element=element,
            default_value=None,
            df=set_edges,
            source=self.metadata,
        )

        return attr
