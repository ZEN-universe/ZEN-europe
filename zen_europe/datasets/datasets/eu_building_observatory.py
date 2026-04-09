from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import pandas as pd

from zen_creator.datasets.datasets.dataset import Dataset


class EUBuildingObservatory(Dataset):
    """Dataset class for EU Building Observatory data."""

    name = "eu_building_observatory"

    def __init__(self, model: Model):
        super().__init__(name="eu_building_observatory", model=model)

    # ------ Metadata properties ------
    @property
    def author(self) -> str:
        return "EU Building Observatory"

    @property
    def publication_year(self) -> int:
        return 2022

    @property
    def url(self) -> str:
        return "https://energy.ec.europa.eu/topics/energy-efficiency/energy-performance-buildings/eu-building-stock-observatory_en"

    # ----- Methods to get data -----
    def load_total_heat_data(self) -> pd.DataFrame:
        total_demand = pd.read_excel(
            self.model.source_path
            / "02-carrier"
            / "heat"
            / "export-eu-buildings-altered.xlsx",
            sheet_name="Compiled",
        ).set_index("Country")
        return total_demand
