from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Element
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings


class StatisticalPocketbookTransport(Dataset[dict[str, pd.Series]]):
    """
    Statistical pocketbook transport dataset class.

    This class implements the specific behavior for the
    Statistical Pocketbook Transport dataset.
    """

    name = "statistical_pocketbook_transport"

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("EU transport in figures: Statistical pocketbook 2022"),
            author=[
                "Directorate-General for Mobility and Transport "
                "(European Commission)"
            ],
            publication="Publication Office of the European Union",
            publication_year=2022,
            url="https://op.europa.eu/en/publication-detail/-/publication/f656ef8e-3e0e-11ed-92ed-01aa75ed71a1/language-en",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "02-carrier" / "transport" / "mileage_EU.xlsx"

    def _set_data(self) -> dict[str, pd.Series]:
        types = ["passenger_mileage", "truck_mileage"]
        time_series_year = self.settings.time.time_series_year
        data: dict[str, pd.Series] = {}
        for t in types:
            sheet = pd.read_excel(self.path, sheet_name=t).set_index("Column1")
            data[t] = sheet[str(time_series_year)].str.replace(" ", "").astype(float)
        return data

    # -------- methods ------------------------
    def get_total_mileage(self, element: Element) -> pd.Series:
        """
        Get the total mileage.

        Returns:
            A pandas Series containing the total mileage.
        """
        data = self.data[element.name]
        data = data.loc[element.model.config.system.set_nodes] * 1000  # million km/a
        data.index.name = "node"
        data.name = "demand"
        return data
