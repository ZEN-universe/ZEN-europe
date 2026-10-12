from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class TYNDPElectricityModellingResults(Dataset[pd.DataFrame]):
    """
    Electricity modelling results dataset class from the TYNDP 2022 scenarios.

    The results report the export capacity of every line of the modelled
    electricity network, for each scenario, climate year and time horizon. A
    border carries one line of the reference grid and one line per expansion
    candidate, so the export capacity of a border is the sum of its lines.
    """

    name = "tyndp_electricity_modelling_results"

    FILE = "220310_Updated_Electricity_Modelling_Results.xlsx"
    SHEET = "Line"
    PARAMETER = "Export Capacity (MW)"
    SCENARIO = "Distributed Energy"
    CLIMATE_YEAR = 2009
    YEAR = 2050
    # lines of the electric vehicle and the hydrogen nodes, which are not part
    # of the electricity transmission network between the nodes of the model
    EXCLUDED_LINES = "V2W|V2g|H2R1|Virtual|H2MT"
    COUNTRY_CODES = {"GR": "EL", "GB": "UK"}

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="TYNDP 2022 Scenarios: Updated Electricity Modelling Results",
            author=["ENTSO-E", "ENTSOG"],
            publication="ENTSO-E and ENTSOG",
            publication_year=2022,
            url="https://2022.entsos-tyndp-scenarios.eu/download/",
            note=(
                f"The export capacity of the {self.SCENARIO} scenario in "
                f"{self.YEAR} for climate year {self.CLIMATE_YEAR} is used."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "power_line"

    def _set_data(self) -> pd.DataFrame:
        """
        The export capacity of every line between two countries, in MW.
        """
        lines = pd.read_excel(self.path / self.FILE, sheet_name=self.SHEET)
        lines = lines[
            (lines["Parameter"] == self.PARAMETER)
            & (lines["Scenario"] == self.SCENARIO)
            & (lines["Climate Year"] == self.CLIMATE_YEAR)
            & (lines["Year"] == self.YEAR)
            & ~lines["Node/Line"].str.contains(self.EXCLUDED_LINES)
        ]
        # the lines of a border share the identifier of the border, the
        # identifier of an expansion candidate carries a suffix behind a space
        border = lines["Node/Line"].str.split(" ").str[0]
        nodes = border.str.split("-", expand=True)
        lines = lines.assign(
            node_from=nodes[0].str[:2].replace(self.COUNTRY_CODES),
            node_to=nodes[1].str[:2].replace(self.COUNTRY_CODES),
        )
        lines = lines[lines["node_from"] != lines["node_to"]]
        return lines[["node_from", "node_to", "Value"]]

    # -------- methods ------------------------
    def get_export_capacity(self, set_nodes: list[str]) -> pd.Series:
        """
        Get the export capacity between the nodes, in GW.

        The capacity is indexed by the country pair it connects.
        """
        lines = self.data[
            self.data["node_from"].isin(set_nodes)
            & self.data["node_to"].isin(set_nodes)
        ]
        capacity = lines.groupby(["node_from", "node_to"])["Value"].sum() / 1000
        capacity.name = "capacity_limit"
        return capacity
