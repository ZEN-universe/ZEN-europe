from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class Eurofer(Dataset[pd.Series]):
    """
    Eurofer dataset class.

    This class implements the specific behavior for the Eurofer dataset.
    """

    name = "eurofer"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("European Steel in Figures 2025"),
            author=["Eurofer"],
            publication="Eurofer",
            publication_year=2025,
            url="https://www.eurofer.eu/publications/brochures-booklets-and-factsheets/european-steel-in-figures-2025",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the Eurofer dataset in kt/y in 2021.

        We assume that all Swiss steel production is imported from the EU.

        The provided number is the total export of steel from the EU to Switzerland in
        2021
        """
        return pd.Series({"CH": 1701})

    # -------- methods ------------------------
    def get_manual_steel_demand_eurofer(self, node: str) -> int:
        """
        Get the demand of steel for CH from the Eurofer dataset.

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
                f" Eurofer dataset."
            )


class WorldSteel(Dataset[pd.Series]):
    """
    World Steel dataset class.

    This class implements the specific behavior for the World Steel dataset.
    """

    name = "worldsteel"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("2023 World Steel in Figures"),
            author=["World Steel"],
            publication="World Steel",
            publication_year=2023,
            url="https://worldsteel.org/data/world-steel-in-figures/world-steel-in-figures-2023/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the World Steel dataset in kt/y in 2023.

        The provided number is the total production of steel in the UK in 2021
        """
        return pd.Series({"UK": 7200})

    # -------- methods ------------------------
    def get_manual_steel_demand_worldsteel(self, node: str) -> int:
        """
        Get the demand of steel for UK from the World Steel dataset.

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
                f" World Steel dataset."
            )


class TradeEconomics(Dataset[pd.Series]):
    """
    Trade Economics dataset class.

    This class implements the specific behavior for the Trade Economics dataset.
    """

    name = "trade_economics"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Norway Steel Production"),
            author=["Trade Economics"],
            publication="Trade Economics",
            publication_year=2020,
            url="https://tradingeconomics.com/norway/steel-production",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the Trade Economics dataset in kt/y in 2020.

        The provided number is the total production of steel in Norway in 2020
        """
        return pd.Series(
            {
                "NO": 61.515
                + 51.833
                + 63.722
                + 50.631
                + 55
                + 57.463
                + 18.087
                + 60
                + 61.248
                + 65
                + 65
                + 41.203
            }
        )

    # -------- methods ------------------------
    def get_manual_steel_demand_trade_economics(self, node: str) -> int:
        """
        Get the demand of steel for NO from the Trade Economics dataset.

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
                f" Trade Economics dataset."
            )
