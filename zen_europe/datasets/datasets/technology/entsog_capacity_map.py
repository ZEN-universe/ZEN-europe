from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.elements import Technology
from zen_creator.utils.attribute import Attribute

from zen_europe.utils.constants import Constants


class ENTSOGCapacityMap(Dataset[pd.DataFrame]):
    """
    System capacity map dataset class from ENTSOG.

    The map reports the technical physical capacity of every interconnection
    point of the European gas transmission system, per direction and in GWh per
    day. Points that connect two different countries are the cross-border
    pipeline capacity between them, whether they are listed as a cross-border
    point, as an import point from a non-EU country or as a point within a
    balancing zone that spans two countries. The entry points of LNG terminals
    are not part of the pipeline capacity and are left out.
    """

    name = "entsog_capacity_map"

    FILE = "System Capacity Map 2026 - Capacities.xlsx"
    SHEET = "Capacities"
    # the table starts below the title and the legend of the map
    HEADER_ROW = 11
    CAPACITY_COLUMN = "Technical physical capacity (GWh/d)"
    # the map reports no commissioning year, so all points are assumed to be
    # available from this year onwards
    CONSTRUCTION_YEAR = 2010
    COUNTRY_CODES = {"GR": "EL", "GB": "UK"}

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="System Capacity Map 2026",
            author=["ENTSOG"],
            publication="ENTSOG",
            publication_year=2026,
            url="https://www.entsog.eu/maps",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "natural_gas"

    def _set_data(self) -> pd.DataFrame:
        """
        The interconnection points that connect two different countries.
        """
        points = pd.read_excel(
            self.path / self.FILE, sheet_name=self.SHEET, header=self.HEADER_ROW
        )
        points = points.rename(columns={self.CAPACITY_COLUMN: "capacity"})

        # the labels of the point sections sit in the column of the point
        # numbers, above the points they apply to
        number = points["Number"].astype(str)
        is_section = points["Number"].notna() & ~number.str.match(r"^\d+(\.\d+)?$")
        points["section"] = points["Number"].where(is_section).ffill()

        for column in ("From CC", "To CC"):
            points[column] = (
                points[column]
                .astype(str)
                .str.strip()
                .replace({"nan": None})  # type: ignore[dict-item]
                .replace(self.COUNTRY_CODES)
            )

        points = points[
            (points["capacity"] > 0)
            & points["From CC"].notna()
            & points["To CC"].notna()
            & (points["From CC"] != points["To CC"])
            & ~points["section"].astype(str).str.contains("LNG")
        ]
        return points[["capacity", "From CC", "To CC"]].rename(
            columns={"From CC": "from_country", "To CC": "to_country"}
        )

    # -------- methods ------------------------
    def get_capacity_existing_pipeline(self, element: Technology) -> Attribute:
        """
        Get the existing cross-border pipeline capacity of each edge.

        The capacity of an edge is the capacity of all interconnection points
        in the direction of the edge, converted from GWh per day into GW.
        """
        set_edges = element.model.energy_system.set_edges.df
        if set_edges is None:
            raise ValueError(
                "The existing pipeline capacity cannot be determined, because "
                "the energy system of the model defines no edges."
            )
        capacity = self.data.groupby(["from_country", "to_country"])["capacity"].sum()
        capacity.index = pd.Index(
            [f"{node_from}-{node_to}" for node_from, node_to in capacity.index]
        )
        capacity = capacity[capacity.index.isin(set_edges.index)].sort_index()
        capacity = capacity / Constants.HOURS_PER_DAY
        capacity.index = pd.MultiIndex.from_arrays(
            [capacity.index, [self.CONSTRUCTION_YEAR] * len(capacity)],
            names=["edge", "year_construction"],
        )
        capacity.name = "capacity_existing"

        attr = element.capacity_existing
        return attr.set_data(
            df=capacity,
            unit="GW",
            source=SourceInformation(
                description=(
                    f"The existing capacity of {element.name} is the technical "
                    f"physical capacity of the interconnection points of the "
                    f"ENTSOG system capacity map, summed over the points of "
                    f"each edge. All pipelines are assumed to exist since "
                    f"{self.CONSTRUCTION_YEAR}, as the map reports no "
                    f"commissioning year."
                ),
                metadata=self.metadata,
            ),
        )
