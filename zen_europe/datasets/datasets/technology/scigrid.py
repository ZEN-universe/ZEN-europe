from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.elements import Element, StorageTechnology, Technology
from zen_creator.utils.attribute import Attribute

from zen_europe.utils.constants import Constants


class SciGridIGGIELGNC1(Dataset[dict[str, pd.DataFrame]]):
    """
    SciGrid IGGIELGNC-1 dataset class for natural gas.

    This class implements the specific behavior for the SciGrid IGGIELGNC-1 dataset.

    Significant data inaccuracies are observed for storage data
    points that are only found in the INET dataset, especially for the UK.
    Thus, we exclude those storages
    with only an INET source ID.
    """

    name = "scigrid_iggielgnc1"

    # the border points report no commissioning year, so all existing
    # pipelines are assumed to be available from this year onwards
    CONSTRUCTION_YEAR = 2010

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("SciGRID_gas IGGIELGNC-1"),
            author=[
                "Jan Diettrich",
                "Adam Pluta",
                "Wided Medjroubi",
                "Jan Dasenbrock",
                "Javier Sandoval",
            ],
            publication="DLR - German Aerospace Center",
            publication_year=2021,
            url="https://zenodo.org/records/5509988",
            note="Significant data inaccuracies are observed for storage data "
            "points that are only found in the INET dataset, especially for the UK. "
            "Thus, we exclude those storages with only an INET source ID."
            "The original folder has more files "
            "(PipeSegments, Nodes, Compressors,...), which are not used here.",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "natural_gas"

    def _set_data(self) -> dict[str, pd.DataFrame]:
        border_points_raw = pd.read_csv(
            self.path / "IGGIELGNC1_BorderPoints.csv", delimiter=";"
        )
        storages_raw = pd.read_csv(self.path / "IGGIELGNC1_Storages.csv", delimiter=";")
        select_storage_data = pd.Series(index=storages_raw.index, data=False)
        for storage in storages_raw.index:
            split_source_id = storages_raw.loc[storage, "source_id"].split(",")
            if len(split_source_id) > 1 or "INET" not in split_source_id[0]:
                select_storage_data[storage] = True
        storages_raw = storages_raw[select_storage_data]
        border_points = border_points_raw["param"].apply(
            lambda item: pd.Series(ast.literal_eval(str(item)))
        )
        border_points = border_points.replace({"GR": "EL", "GB": "UK"})
        storages = storages_raw["param"].apply(
            lambda item: pd.Series(ast.literal_eval(str(item)))
        )
        storages["nuts_id_0"] = storages_raw["country_code"].replace(
            {"GR": "EL", "GB": "UK"}
        )
        return {"border_points": border_points, "storages": storages}

    def get_capacity_existing_pipeline(self, element: Technology) -> Attribute:
        """
        Get the existing cross-border pipeline capacity of each edge.

        The capacity of an edge is the capacity of all border points in the
        direction of the edge, plus the reverse capacity of all border points
        in the opposite direction. The border points report their capacity in
        million m3 per day, which the gross calorific value converts into
        GWh per day.
        """
        set_edges = element.model.energy_system.set_edges.df
        if set_edges is None:
            raise ValueError(
                "The existing pipeline capacity cannot be determined, because "
                "the energy system of the model defines no edges."
            )
        border_points = self.data["border_points"]
        capacity_from_to = (
            border_points["max_cap_from_to_M_m3_per_d"]
            * border_points["GCV_mean_kWh_per_m3"]
        )
        capacity_to_from = (
            border_points["max_cap_to_from_M_m3_per_d"]
            * border_points["GCV_mean_kWh_per_m3"]
        )

        capacity_existing = {}
        for edge in set_edges.index:
            node_from = set_edges.loc[edge, "node_from"]
            node_to = set_edges.loc[edge, "node_to"]
            along_edge = (border_points["from_country"] == node_from) & (
                border_points["to_country"] == node_to
            )
            against_edge = (border_points["from_country"] == node_to) & (
                border_points["to_country"] == node_from
            )
            capacity = (
                capacity_from_to[along_edge].sum()
                + capacity_to_from[against_edge].sum()
            )
            if capacity > 0:
                capacity_existing[(edge, self.CONSTRUCTION_YEAR)] = (
                    capacity / Constants.HOURS_PER_DAY
                )

        data = pd.Series(capacity_existing, name="capacity_existing")
        data.index = pd.MultiIndex.from_tuples(
            data.index, names=["edge", "year_construction"]
        )
        attr = element.capacity_existing
        return attr.set_data(
            df=data,
            unit="GW",
            source=SourceInformation(
                description=(
                    f"The existing capacity of {element.name} is the "
                    f"cross-border capacity of the border points of the "
                    f"SciGRID_gas dataset, summed over both directions of "
                    f"each edge. All pipelines are assumed to exist since "
                    f"{self.CONSTRUCTION_YEAR}, as the border points report "
                    f"no commissioning year."
                ),
                metadata=self.metadata,
            ),
        )

    def get_pipeline_availability(
        self, element: Element
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Get the pipeline availability data.

        This function retrieves the pipeline availability data from the SciGrid
        IGGIELGNC-1 dataset.
        """
        border_points = self.data["border_points"]
        import_gas = pd.DataFrame(
            index=element.model.config.system.set_nodes,
            columns=["import", "export"],
            data=0,
            dtype=float,
        )
        import_gas_RU = pd.Series(
            index=element.model.config.system.set_nodes, data=0, dtype=float
        )
        nodes_RU = ["RU", "UA", "BY", "MD"]
        nodes_turkstream = {"from": "TR", "to": "BG"}
        for node in element.model.config.system.set_nodes:
            import_gas_node = border_points[
                (border_points["to_country"] == node)
                & (
                    ~border_points["from_country"].isin(
                        element.model.config.system.set_nodes
                    )
                )
            ]
            export_gas_node = border_points[
                (border_points["from_country"] == node)
                & (
                    ~border_points["to_country"].isin(
                        element.model.config.system.set_nodes
                    )
                )
            ]
            import_gas_node = import_gas_node[import_gas_node["from_country"] != "XX"]
            export_gas_node = export_gas_node[export_gas_node["to_country"] != "XX"]
            if not import_gas_node.empty:
                import_gas.loc[node, "import"] = (
                    import_gas_node["max_cap_from_to_M_m3_per_d"]
                    * import_gas_node["GCV_mean_kWh_per_m3"]
                ).sum()
                import_gas.loc[node, "export"] = (
                    import_gas_node["max_cap_to_from_M_m3_per_d"]
                    * import_gas_node["GCV_mean_kWh_per_m3"]
                ).sum()
                # import from "Russian" countries
                if import_gas_node["from_country"].isin(nodes_RU).any():
                    import_gas_node_RU = import_gas_node[
                        import_gas_node["from_country"].isin(nodes_RU)
                    ]
                    import_gas_RU.loc[node] = (
                        import_gas_node_RU["max_cap_from_to_M_m3_per_d"]
                        * import_gas_node_RU["GCV_mean_kWh_per_m3"]
                    ).sum()
                # TurkStream
                elif (
                    import_gas_node["from_country"] == nodes_turkstream["from"]
                ).any() and (
                    import_gas_node["to_country"] == nodes_turkstream["to"]
                ).any():
                    import_gas_node_RU = import_gas_node[
                        (import_gas_node["from_country"] == nodes_turkstream["from"])
                        & (import_gas_node["to_country"] == nodes_turkstream["to"])
                    ]
                    import_gas_RU.loc[node] = (
                        import_gas_node_RU["max_cap_from_to_M_m3_per_d"]
                        * import_gas_node_RU["GCV_mean_kWh_per_m3"]
                    ).sum()
            elif not export_gas_node.empty:
                import_gas.loc[node, "export"] = (
                    export_gas_node["max_cap_from_to_M_m3_per_d"]
                    * export_gas_node["GCV_mean_kWh_per_m3"]
                ).sum()
                import_gas.loc[node, "import"] = (
                    export_gas_node["max_cap_to_from_M_m3_per_d"]
                    * export_gas_node["GCV_mean_kWh_per_m3"]
                ).sum()
                # export to "Russian" countries
                if export_gas_node["to_country"].isin(nodes_RU).any():
                    export_gas_node_RU = export_gas_node[
                        export_gas_node["to_country"].isin(nodes_RU)
                    ]
                    import_gas_RU.loc[node] = (
                        export_gas_node_RU["max_cap_to_from_M_m3_per_d"]
                        * export_gas_node_RU["GCV_mean_kWh_per_m3"]
                    ).sum()
                # TurkStream
                elif (
                    export_gas_node["to_country"] == nodes_turkstream["from"]
                ).any() and (
                    export_gas_node["from_country"] == nodes_turkstream["to"]
                ).any():
                    export_gas_node_RU = export_gas_node[
                        (export_gas_node["to_country"] == nodes_turkstream["from"])
                        & (export_gas_node["from_country"] == nodes_turkstream["to"])
                    ]
                    import_gas_RU.loc[node] = (
                        export_gas_node_RU["max_cap_to_from_M_m3_per_d"]
                        * export_gas_node_RU["GCV_mean_kWh_per_m3"]
                    ).sum()
        import_gas = import_gas[(import_gas != 0).any(axis=1)].sort_index()
        import_gas_RU = import_gas_RU[import_gas_RU != 0].sort_index()
        import_gas /= 24
        import_gas.index.name = "node"
        import_gas_RU /= 24
        import_gas_RU.index.name = "node"
        return import_gas, import_gas_RU

    def get_mean_gcv(self) -> pd.Series:
        """
        Get the mean gross calorific value of natural gas per country in kWh/m3.

        The value is averaged over the border points that deliver gas to the
        country.
        """
        border_points = self.data["border_points"]
        return border_points.groupby("to_country")["GCV_mean_kWh_per_m3"].mean()

    def get_capacity_existing(
        self, element: StorageTechnology, power: bool = True
    ) -> Attribute:
        """
        Get the existing natural gas storage capacity per node and construction year.

        Storages that start operating after the reference year or that are
        decommissioned before it are dropped. Storages without a reported start
        year are dropped as well, since they are either virtual storages that
        aggregate the individual sites of an operator, or entries whose
        capacities are filled with the median of the reported ones. The power
        capacity is the larger of the injection and the withdrawal rate, the
        energy capacity is the working gas volume. The volumes are converted
        with the mean gross calorific value of the country the storage is in.

        Args:
            element: The element for which to get the existing capacity.
            power: If True, returns the power capacity; if False, the energy capacity.
        """
        reference_year = element.settings.time.reference_year
        storages = self.data["storages"].copy()
        storages = storages[storages["start_year"] < reference_year]
        storages = storages[~(storages["end_year"] <= reference_year)]
        storages.loc[:, "start_year"] = storages["start_year"].astype(int)
        storages = storages.groupby(["nuts_id_0", "start_year"]).sum(numeric_only=True)

        if power:
            # 1e6 m3/d * kWh/m3 = GWh/d
            capacity = storages[
                ["max_cap_pipe2store_M_m3_per_d", "max_cap_store2pipe_M_m3_per_d"]
            ].max(axis=1)
            capacity = capacity / Constants.HOURS_PER_DAY
            attr = element.capacity_existing
            unit = "GW"
        else:
            # 1e6 m3 * kWh/m3 = GWh
            capacity = storages["max_workingGas_M_m3"]
            attr = element.capacity_existing_energy
            unit = "GWh"

        gcv = self.get_mean_gcv()
        gcv_storages = gcv.reindex(storages.index.get_level_values("nuts_id_0")).fillna(
            gcv.mean()
        )
        capacity = capacity * gcv_storages.to_numpy()

        set_nodes = element.model.config.system.set_nodes
        capacity = capacity[
            capacity.index.get_level_values("nuts_id_0").isin(set_nodes)
        ]
        capacity = capacity[capacity > 0].sort_index()
        capacity.index = capacity.index.set_names(["node", "year_construction"])
        capacity.name = attr.name

        source = SourceInformation(
            description=(
                f"The existing capacity of {element.name} is derived from the "
                "storages of the SciGRID_gas IGGIELGNC-1 dataset. The volumes are "
                "converted to energy with the mean gross calorific value of the "
                "border points of the respective country."
            ),
            metadata=self.metadata,
        )
        return attr.set_data(df=capacity, source=source, unit=unit)
