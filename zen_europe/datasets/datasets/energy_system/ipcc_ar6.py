from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class IPCCAR6(Dataset[pd.DataFrame]):
    """
    Dataset class for the IPCC AR6 data.

    """

    name = "ipcc_ar6"
    AR6_BUDGET_START_YEAR = 2020

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Climate Change 2021 The Physical Science Basis"),
            author=["IPCC"],
            publication=(
                "Sixth Assessment Report of the Intergovernmental Panel on Climate "
                "Change"
            ),
            publication_year=2021,
            url="https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_SPM_final.pdf#page=33",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> dict[str, pd.Series]:
        """
        Set data for the remaining carbon budget for different temperature targets and
        probabilities.

        In GtCO2, based on IPCC AR6, Table SPM.2, page 33.
        """
        budget = {
            1.5: {
                0.17: 900,
                0.33: 650,
                0.50: 500,
                0.67: 400,
                0.83: 300,
            },
            1.7: {0.17: 1450, 0.33: 1050, 0.50: 850, 0.67: 700, 0.83: 550},
            2: {0.17: 2300, 0.33: 1700, 0.50: 1350, 0.67: 1150, 0.83: 900},
        }

        data = pd.DataFrame(budget)
        return data

    # -------- methods ------------------------
    def get_remaining_carbon_budget(
        self, temperature_target: float, probability: float
    ) -> float:
        """
        Get the remaining carbon budget for a given temperature target and probability.

        Args:
            temperature_target (float): The temperature target in degrees Celsius (e.g.,
                1.5, 1.7, 2).
            probability (float): The probability of staying below the temperature target
                (e.g., 0.17, 0.33, 0.50, 0.67, 0.83).
        """
        if temperature_target not in self.data.columns:
            raise ValueError(
                f"Temperature target {temperature_target}°C is not available. "
                f"Available targets: {list(self.data.columns)}"
            )
        if probability not in self.data.index:
            raise ValueError(
                f"Probability {probability} is not available. "
                f"Available probabilities: {list(self.data.index)}"
            )
        remaining_budget = self.data.loc[probability, temperature_target]
        return remaining_budget
