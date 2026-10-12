from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Technology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class EuroCalliope(Dataset[pd.Series]):
    """
    EuroCalliope dataset class for potential capacity.

    """

    name = "euro_calliope"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Trade-Offs between Geographic Scale, Cost, and Infrastructure "
                "Requirements for Fully Renewable Electricity in Europe"
            ),
            author=[
                "Tim Tröndle",
                "Johan Lilliestam",
                "Stefano Marelli",
                "Stefan Pfenninger",
            ],
            publication="Joule",
            publication_year=2020,
            url="https://www.sciencedirect.com/science/article/pii/S2542435120303366",
            doi="https://doi.org/10.1016/j.joule.2020.07.018",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """
        Set the data for the EuroCalliope dataset.
        Note: The PV is roof-top PV, not ground-mounted PV.
        Ground-mounted PV is competing with wind onshore.
        Onshore wind is "wind_onshore_monopoly".

        """
        data: dict[tuple[str, str], float] = {}
        data[("wind_onshore", "NO")] = 11.045267511637062 * 100
        data[("wind_offshore", "NO")] = 8.202832823416685 * 100
        data[("photovoltaics", "NO")] = 0.28532725082404814 * 100
        data[("wind_onshore", "CH")] = 0.4275919580817223 * 100
        data[("wind_offshore", "CH")] = 0.0
        data[("photovoltaics", "CH")] = 0.5971794910850416 * 100
        return pd.Series(data, name="potential_capacity_gw")

    # -------- methods ------------------------
    def get_capacity_limit(self, element: Technology, node: str) -> float:
        """
        Get the potential capacity for renewable technologies.

        Args:
            element: The element for which to get the potential capacity.

        Returns:
            float: The potential capacity of the element at the node in GW.
        """
        if (element.name, node) not in self.data.index:
            raise ValueError(
                f"Potential capacity data for {element.name} in {node} is not "
                "available in the EuroCalliope dataset."
            )
        return self.data.loc[(element.name, node)]
