from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class Eurofer(Dataset[dict[str, pd.DataFrame]]):
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

    def _set_data(self) -> dict[str, pd.DataFrame]:
        """sets the manual data for the Eurofer dataset in kt/y.

        crude_steel_output: the crude steel output per country from 2020 to 2024,
        table "Crude steel output per country" (p. 13). Portugal is part of "Others".

        exports: the total export of steel from the EU to Switzerland in 2021. We
        assume that all Swiss steel production is imported from the EU.
        """
        crude_steel_output = pd.DataFrame(
            {
                "AT": [6765, 7884, 7512, 7133, 7130],
                "BE": [6119, 6909, 7030, 5864, 7135],
                "BG": [484, 548, 482, 489, 450],
                "HR": [45, 185, 169, 212, 153],
                "CZ": [4450, 4788, 4262, 3369, 2548],
                "FI": [3498, 4340, 3538, 3811, 3664],
                "FR": [11596, 13947, 12234, 10011, 10753],
                "DE": [35679, 40241, 36860, 35395, 37234],
                "EL": [1308, 1498, 1543, 1181, 1336],
                "HU": [1513, 1100, 857, 477, 232],
                "IT": [20379, 24412, 21599, 21055, 20007],
                "LU": [1886, 2073, 1875, 1900, 1825],
                "NL": [6054, 6620, 6143, 4677, 6395],
                "PL": [7856, 8454, 7407, 6428, 7113],
                "RO": [2790, 3375, 2625, 1622, 1364],
                "SK": [3444, 4863, 3872, 4377, 3866],
                "SI": [623, 701, 623, 559, 598],
                "ES": [11142, 14234, 11464, 11352, 11832],
                "SE": [4383, 4657, 4382, 4235, 4002],
            },
            index=range(2020, 2025),
        ).T
        return {
            "crude_steel_output": crude_steel_output,
            "exports": pd.DataFrame({"exports": {"CH": 1701}}),
        }

    # -------- methods ------------------------
    def get_crude_steel_output(self) -> pd.Series:
        """
        Get the mean crude steel output per country from 2020 to 2024 in kt/y.
        """
        return self.data["crude_steel_output"].mean(axis=1)

    def get_manual_steel_demand_eurofer(self, node: str) -> int:
        """
        Get the demand of steel for CH from the Eurofer dataset.

        Returns the demand in kt/y for the given node.

        Args:
            node: The node for which to get the demand.

        Returns:
            The demand in kt/y for the given node.
        """
        exports = self.data["exports"]["exports"]
        if node in exports.index:
            return exports.loc[node]
        else:
            raise ValueError(
                f"Node {node} not found in the manual values of the Eurofer dataset."
            )


    # -------- methods ------------------------


class WorldSteelInFigures2025(Dataset[pd.DataFrame]):
    """
    World Steel in Figures 2025 dataset class.

    This class implements the specific behavior for the World Steel in Figures 2025
    dataset.
    """

    name = "worldsteel_2025"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("World Steel in Figures 2025"),
            author=["World Steel Association"],
            publication="World Steel Association",
            publication_year=2025,
            url="https://worldsteel.org/wp-content/uploads/World-Steel-in-Figures-2025.pdf",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        """sets the crude steel production in Mt and its oxygen and electric shares
        in % per country in 2024, table "Crude steel production by process 2024"
        (p. 10).

        The listed EU countries add up to the EU27 total, so the other EU countries
        produce no crude steel.
        """
        return pd.DataFrame(
            {
                "AT": [7.1, 91.6, 8.4],
                "BE": [7.1, 71.2, 28.8],
                "BG": [0.5, 0, 100.0],
                "HR": [0.2, 0, 100.0],
                "CZ": [2.5, 94.7, 5.3],
                "FI": [3.7, 63.2, 36.8],
                "FR": [10.8, 62.7, 37.3],
                "DE": [37.2, 70.9, 29.1],
                "EL": [1.3, 0, 100.0],
                "HU": [0.2, 0, 100.0],
                "IT": [20.0, 10.7, 89.3],
                "LU": [1.8, 0, 100.0],
                "NL": [6.4, 100.0, 0],
                "PL": [7.1, 54.2, 45.8],
                "PT": [1.9, 0, 100.0],
                "RO": [1.4, 30.9, 69.1],
                "SK": [3.9, 89.9, 10.1],
                "SI": [0.6, 0, 100.0],
                "ES": [11.9, 30.7, 69.3],
                "SE": [4.0, 65.8, 34.2],
                "UK": [4.0, 71.7, 28.3],
            },
            index=["production", "oxygen", "electric"],
        ).T

    # -------- methods ------------------------
    def get_crude_steel_production(self) -> pd.Series:
        """
        Get the crude steel production per country in 2024 in kt/y.
        """
        return self.data["production"] * 1000

    def get_secondary_steel_share(self) -> pd.Series:
        """
        Get the electric arc furnace share of the crude steel production per country
        in 2024.
        """
        return self.data["electric"] / 100


class GlobalIronSteelTracker(Dataset[pd.Series]):
    """
    Global Iron and Steel Tracker dataset class.

    This class implements the specific behavior for the Global Iron and Steel Tracker
    dataset.
    """

    name = "global_iron_steel_tracker"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Global Iron and Steel Tracker"),
            author=["Global Energy Monitor"],
            publication="Global Energy Monitor",
            publication_year=2025,
            url="https://globalenergymonitor.org/projects/global-iron-and-steel-tracker/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the electric arc furnace share of the crude steel production of the
        countries that World Steel in Figures does not list separately.

        The tracker lists Stahl Gerlafingen (CH) and Celsa Nordic Mo i Rana (NO) as
        electric arc furnace plants:
        https://gem.wiki/Stahl_Gerlafingen_steel_plant
        https://gem.wiki/Celsa_Nordic_steel_plant
        """
        return pd.Series({"CH": 1.0, "NO": 1.0})

    # -------- methods ------------------------
    def get_secondary_steel_share(self) -> pd.Series:
        """
        Get the electric arc furnace share of the crude steel production per country.
        """
        return self.data


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
