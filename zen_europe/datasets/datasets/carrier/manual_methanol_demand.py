from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class WITS(Dataset[pd.Series]):
    """
    WITS (World Integrated Trade Solution) dataset class by the World Bank.

    This class implements the specific behavior for the WITS dataset.
    """

    name = "wits"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Methanol Imports and Exports by Country"),
            author=["World Bank"],
            publication="World Bank",
            publication_year=2022,
            url="https://wits.worldbank.org/trade/comtrade/en/country/CHE/year/2022/tradeflow/Imports/partner/ALL/product/290511",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the WITS dataset in kt/y in 2022.

        The provided number is the total production of methanol in CH in 2022.
        The import is calculated from the total trade value of methanol divided by the
        weighted average price of all methanol imports.
        The export is obtained from
        https://wits.worldbank.org/trade/comtrade/en/country/ALL/year/2022/tradeflow/Exports/partner/WLD/product/290511
        """
        return pd.Series({"CH": 33.48552246 - 2.415940})

    # -------- methods ------------------------
    def get_manual_methanol_demand_wits(self, node: str) -> int:
        """
        Get the demand of methanol for CH from the WITS dataset.

        Returns the demand in kt/y for the given node.

        Args:
            node: The node for which to get the demand.

        Returns:
            The demand in kt/y for the given node.
        """
        if node in self.data.index:
            return self.data.loc[node]
        else:
            raise ValueError(
                f"Node {node} not found in the manual values of the" f" WITS dataset."
            )


class Equinor(Dataset[pd.Series]):
    """
    Equinor dataset class.

    This class implements the specific behavior for the Equinor dataset.
    """

    name = "equinor"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Tjeldbergodden industrial facility"),
            author=["Equinor"],
            publication="Equinor",
            publication_year=2026,
            url="https://www.equinor.com/energy/tjeldbergodden",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the Equinor dataset in kt/y in 2026.

        The provided number is the total production of methanol at the Tjeldbergodden
        facility in 2026.
        """
        return pd.Series({"NO": 900})

    # -------- methods ------------------------
    def get_manual_methanol_demand_equinor(self, node: str) -> int:
        """
        Get the demand of methanol for the UK from the Equinor dataset.

        Returns the demand in kt/y for the given node.

        Args:
            node: The node for which to get the demand.

        Returns:
            The demand in kt/y for the given node.
        """
        if node in self.data.index:
            return self.data.loc[node]
        else:
            raise ValueError(
                f"Node {node} not found in the manual values of the"
                f" Equinor dataset."
            )


class ChemAnalyst(Dataset[pd.Series]):
    """
    ChemAnalyst dataset class.

    This class implements the specific behavior for the ChemAnalyst dataset.
    """

    name = "chemanalyst"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("UK Methanol Market Analysis"),
            author=["World Bank"],
            publication="World Bank",
            publication_year=2023,
            url="https://www.chemanalyst.com/industry-report/united-kingdom-methanol-market-206",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the ChemAnalyst dataset in kt/y in 2023.

        The provided number is the total production of methanol in the UK in 2023.
        """
        return pd.Series({"UK": 530})

    # -------- methods ------------------------
    def get_manual_methanol_demand_chemanalyst(self, node: str) -> int:
        """
        Get the demand of methanol for the UK from the ChemAnalyst dataset.

        Returns the demand in kt/y for the given node.

        Args:
            node: The node for which to get the demand.

        Returns:
            The demand in kt/y for the given node.
        """
        if node in self.data.index:
            return self.data.loc[node]
        else:
            raise ValueError(
                f"Node {node} not found in the manual values of the"
                f" ChemAnalyst dataset."
            )

    def get_total_european_demand(self) -> int:
        """
        Get the total European demand of methanol from the ChemAnalyst dataset
        to correct the overall demand. The issue with AIDRES demand is that
        it assumes 0 demand in 2018/the beginning of the dataset, which is not correct.
        Therefore, we use the 2030 demand from AIDRES but scale
        it to the total European demand in 2023 from ChemAnalyst.

        Returns the total European demand in kt/y.
        https://www.chemanalyst.com/industry-report/europe-methanol-market-215

        Returns:
            The total demand in kt/y.
        """
        return 11300
