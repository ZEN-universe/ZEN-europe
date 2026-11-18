from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

# branches 1 (food), 3 (paper and printing) and 6 (other non-metallic minerals)
BRANCHES = [1, 3, 6]
SHEETS = {
    "Holz": "biomass",
    "Erdgas": "natural_gas",
    "Heizöl extra-leicht": "oil",
    "Heizöl mittel und schwer": "oil",
    "Kohle": "coal",
    "Industrieabfälle": "waste",
}


class BFEIndustry(Dataset[pd.DataFrame]):
    """
    BFE industry dataset class.

    Fuel consumption of the Swiss industry branches, from the BFE statistics of the
    energy consumption in industry and services.
    """

    name = "bfe_industry"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Energieverbrauch in der Industrie und im Dienstleistungssektor",
            author=["Bundesamt für Energie BFE"],
            publication="Bundesamt für Energie BFE",
            publication_year=2025,
            url="https://pubdb.bfe.admin.ch/de/publication/download/12230",
            note="Branches 1 (food), 3 (paper) and 6 (other non-metallic minerals).",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "industry" / "BFE2025.xlsx"

    def _set_data(self) -> pd.DataFrame:
        sheets = pd.read_excel(self.path, sheet_name=list(SHEETS), header=None)
        # TJ
        return pd.concat(
            {sheet: self._extract_sheet(df) for sheet, df in sheets.items()},
            names=["sheet", "branch"],
        )

    @staticmethod
    def _extract_sheet(sheet: pd.DataFrame) -> pd.DataFrame:
        """Extract the yearly consumption of the selected branches."""
        (header_row,) = sheet.index[sheet[0] == "BranchenNr."]
        data = sheet.iloc[header_row + 1 :].set_index(0).iloc[:, 2:]
        data.columns = sheet.iloc[header_row, 3:].astype(int).to_numpy()
        return data.loc[BRANCHES].astype(float)

    def get_fuel_consumption(self, year: int) -> pd.Series:
        """
        Get the fuel consumption of the food, paper and mineral branches.

        Args:
            year (int): The latest year of the data.

        Returns:
            pd.Series: Fuel consumption in TJ per boiler fuel, in the latest year up
                to `year`.
        """
        latest_year = max(y for y in self.data.columns if y <= year)
        consumption = self.data[latest_year]
        return consumption.groupby(
            consumption.index.get_level_values("sheet").map(SHEETS)
        ).sum()
