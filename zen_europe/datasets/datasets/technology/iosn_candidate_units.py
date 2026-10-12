from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class IoSNCandidateUnits(Dataset[pd.DataFrame]):
    """
    Investment candidates dataset class from the TYNDP 2022 system needs study.

    The identification of system needs (IoSN) screens the European network for
    needs in terms of an increase of the interconnection capacities. The
    workbook holds Appendix 2 of the implementation guidelines of that study,
    which lists the capacity increases that were proposed to the optimiser,
    both projects of the TYNDP 2022 portfolio and conceptual increases that do
    not correspond to an existing project. A border carries one row per
    candidate, so its total increase is the sum of its rows.
    """

    name = "iosn_candidate_units"

    FILE = "IoSN_candidate_units_increase.xlsx"
    SHEET = "Append1"
    CAPACITY_COLUMN = "Direct capacity increase (in MW)"
    COUNTRY_CODES = {"GR": "EL", "GB": "UK"}

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="TYNDP 2022 System Needs Study: Implementation Guidelines",
            author=["ENTSO-E"],
            publication="ENTSO-E",
            publication_year=2023,
            note=(
                "Appendix 2 of the final version of May 2023, investment "
                "candidates (capacity increases) and cost assumptions, "
                "documented in IoSN-IG.pdf next to the data. The candidates "
                "are screened for the 2030 and the 2040 time horizon of the "
                "TYNDP 2022 National Trends scenarios."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "power_line"

    def _set_data(self) -> pd.DataFrame:
        """
        The capacity increase of every candidate between two countries, in MW.
        """
        candidates = pd.read_excel(self.path / self.FILE, sheet_name=self.SHEET)
        candidates.columns = candidates.columns.str.replace("\n", " ")
        nodes = candidates["Border"].str.split("-", expand=True)
        candidates = candidates.assign(
            node_from=nodes[0].str[:2].replace(self.COUNTRY_CODES),
            node_to=nodes[1].str[:2].replace(self.COUNTRY_CODES),
        )
        candidates = candidates[candidates["node_from"] != candidates["node_to"]]
        return candidates[["node_from", "node_to", self.CAPACITY_COLUMN]]

    # -------- methods ------------------------
    def get_capacity_increase(self, set_nodes: list[str]) -> pd.Series:
        """
        Get the capacity increase of all candidates between the nodes, in GW.

        The increase is indexed by the country pair it connects.
        """
        candidates = self.data[
            self.data["node_from"].isin(set_nodes)
            & self.data["node_to"].isin(set_nodes)
        ]
        increase = (
            candidates.groupby(["node_from", "node_to"])[self.CAPACITY_COLUMN].sum()
            / 1000
        )
        increase.name = "capacity_limit"
        return increase
