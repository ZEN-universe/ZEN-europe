from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation


class Stark2025(Dataset[pd.Series]):
    """
    Dataset class for the cost of industrial waste-heat recovery from Stark et al.
    (2025).
    """

    name = "stark2025"

    MONEY_YEAR = 2025

    # investment in the waste-heat recovery of a heat pump (USD/kWth)
    WASTE_HEAT_RECOVERY_CAPEX = 1788.0

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Waste heat is mostly a waste of time",
            author=["Addison Killean Stark", "Ashwin Salvi", "Todd Bandhauer"],
            publication="Joule 9, 102157",
            publication_year=2025,
            url="https://doi.org/10.1016/j.joule.2025.102157",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        data: dict[str, float] = {}
        return pd.Series(data)

    # -------- methods ------------------------
    def get_capex_waste_heat_recovery(self, price_year: int) -> float:
        """
        Get the investment in the waste-heat recovery of a heat pump, in Euro/kW of
        `price_year`.

        The 1,788 USD/kWth of 2025 are converted with the ECB dollar-to-euro
        exchange rate of 2025 and the ECB inflation from 2025 to `price_year`.

        Returns:
            float: The investment in Euro/kW.
        """
        dollar2euro = ECBDollar2Euro(self.source_path).get_dollar2euro(
            year=self.MONEY_YEAR
        )
        inflation = ECBInflation(self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=price_year
        )
        return self.WASTE_HEAT_RECOVERY_CAPEX * dollar2euro * inflation
