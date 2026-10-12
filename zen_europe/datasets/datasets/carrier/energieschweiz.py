from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute

_MAP_TECHNOLOGY = {
    "Heizöl": "oil_boiler",
    "Erdgas": "natural_gas_boiler",
    "Holz": "biomass_boiler",
    "El. Widerstandsheizungen": "electrode_boiler",
    "Fernwärme": "district_heating_grid",
    "El. Ohm'sche Anlagen": "electrode_boiler",
}


class EnergieSchweiz(Dataset[pd.Series]):
    """
    EnergieSchweiz dataset class.

    This class implements the data from the Liste "Thermische Netze" -
    Auswertungsbericht 2021
    """

    name = "energieschweiz"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Liste 'Thermische Netze' - Auswertungsbericht 2021"),
            author=["Diego Hangartner", "Andreas Hurni"],
            publication="EnergieSchweiz",
            publication_year=2021,
            url="https://pubdb.bfe.admin.ch/de/publication/download/10878",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """Share of district heating technologies in Switzerland.

        Table 1, p.5.
        """
        data = {
            "waste_boiler_DH": 0.45,
            "biomass_boiler_DH": 0.30 + 0.01,
            "natural_gas_boiler_DH": 0.02 + 0.04,
            "heat_pump_DH": 0.04 + 0.02 + 0.02 + 0.04,
        }
        data = pd.Series(data, name="share")
        data.index.name = "technology"
        data = data / data.sum()
        return data

    # -------- methods ------------------------
    def get_share_DH(self) -> Attribute:
        """
        Get the split of district heating heat demand into technology categories.
        """
        return self.data
