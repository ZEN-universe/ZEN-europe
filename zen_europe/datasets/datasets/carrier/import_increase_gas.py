from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class ImportIncreaseGas(Dataset[pd.DataFrame]):
    """
    Import increase dataset class for natural gas.

    This class implements the specific behavior for the import increase dataset.
    """

    name = "import_increase_gas"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "The EU plan to reduce Russian gas imports by two-thirds "
                "by the end of 2022: Practical realities and implications"
            ),
            author=["Mike Fulwood", "Anouk Honoré", "Jack Sharples", "Marshall Hall"],
            publication="The Oxford Institute for Energy Studies",
            publication_year=2022,
            url="https://www.oxfordenergy.org/publications/the-eu-plan-to-reduce-russian-gas-imports-by-two-thirds-by-the-end-of-2022-practical-realities-and-implications/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.S:
        return pd.Series({"lng": 55, "norway": 2, "azerbaijan": 2.85, "algeria": 2})

    def get_import_increase(self, region: str) -> pd.DataFrame:
        """
        Get the import increase data for natural gas.

        This function retrieves the import increase data for natural gas.
        """
        if region not in self.data.index:
            raise ValueError(
                f"Region '{region}' not found in the import increase data."
            )
        return self.data[region]
