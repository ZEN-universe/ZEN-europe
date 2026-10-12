from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class Energifaktanorge(Dataset[pd.Series]):
    """
    Energifaktanorge dataset class.

    This class implements the specific behavior for the Energifaktanorge dataset.
    """

    name = "energifaktanorge"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Energy use by sector"),
            author=["Energifaktanorge"],
            publication="Energifaktanorge",
            publication_year=2025,
            url="https://energifaktanorge.no/en/norsk-energibruk/energibruken-i-ulike-sektorer/#household-and-service-industries",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series()

    # -------- methods ------------------------
    def get_service_demand(self) -> pd.Series:
        """
        Get the NO heat demand for the Service sector.
        """
        total_energy_service = 36 * 1000  # GWh
        share_space_heating = 0.4
        share_water_heating = 0.1
        data_ser = pd.Series(
            {
                "space_heating": total_energy_service * share_space_heating,
                "water_heating": total_energy_service * share_water_heating,
            }
        )
        return data_ser
