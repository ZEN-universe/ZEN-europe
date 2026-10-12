from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from datetime import datetime

import pandas as pd
from zen_creator import Carrier, Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants

_MAPPING_TECHNOLOGY_NAMES = {
    "Elektrizität": "electricity",
    "Erdölprodukte": "oil",
    "Fernwärme": "district_heating",
    "Gas": "natural_gas",
    "Holzenergie": "biomass",
    "Kernbrennstoffe": "uranium",
    "Kohle": "hard_coal",
    "Müll und Industrieabfälle": "waste",
    "Rohöl": "crude_oil",
}


class SwissEnergyBalance(Dataset[pd.DataFrame]):
    """Dataset class for Swiss energy balance data."""

    name = "swiss_energy_balance"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Swiss Energy Balance",
            author=["Swiss Federal Statistical Office"],
            publication="Swiss Federal Statistical Office",
            publication_year=datetime.now().year,
            url="https://opendata.swiss/en/dataset/energiebilanz-der-schweiz",
        )

    def _set_path(self) -> Path | None:
        # Swiss energy balance data is accessed directly via URL, no local path needed
        return None

    # ----- Property overwrites -----

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Method to get the Swiss energy balance data."""
        url = "https://www.uvek-gis.admin.ch/BFE/ogd/115/ogd115_gest_bilanz.csv"
        df = pd.read_csv(url)

        data = df.set_index(["Energietraeger", "Rubrik", "Jahr"]).squeeze().unstack()

        data = data / Constants.GJ_PER_MWH  # from TJ to GWh

        new_index = data.index.map(
            lambda x: (_MAPPING_TECHNOLOGY_NAMES.get(x[0], x[0]), x[1])
        )
        data.index = new_index
        data.index.names = ["element", "category"]

        return data

    # ------ Outward facing functions ------

    def get_data(self, year: int, element: Carrier) -> pd.Series:
        """Get the data for a specific year and element."""
        if element.name not in self.data.index.get_level_values("element"):
            raise ValueError(
                f"Element '{element.name}' not found in the"
                f"Swiss Energy Balance dataset."
            )
        return self.data.loc[element.name, year]

    def get_coal_availability(self, year: int, element: Carrier) -> float:
        """Get the availability for coal."""
        data = self.get_data(year=year, element=element)
        return data.loc["Bruttoverbrauch"]

    def get_oil_availability(self, year: int, element: Carrier) -> float:
        """Get the availability for oil."""
        data = self.get_data(year=year, element=element)
        return data.loc["Endverbrauch - Total"]

    def get_waste_availability(
        self, year: int, element: Carrier, include_industry: bool = False
    ) -> float:
        """Get the availability for waste."""
        data = self.get_data(year=year, element=element)
        if include_industry:
            return data.loc["Bruttoverbrauch"]
        else:
            return data.loc["Bruttoverbrauch"] - data.loc["Endverbrauch - Industrie"]


class SwissOilBalance(Dataset[pd.DataFrame]):
    """Dataset class for Swiss oil balance data."""

    name = "swiss_oil_balance"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Swiss Crude Oil Balance",
            author=["Swiss Federal Statistical Office"],
            publication="Swiss Federal Statistical Office",
            publication_year=datetime.now().year,
            url="https://opendata.swiss/de/dataset/schweizerische-gesamtenergiestatistik-erdolbilanz-der-schweiz",
        )

    def _set_path(self) -> Path | None:
        # Swiss oil balance data is accessed directly via URL, no local path needed
        return None

    # ----- Property overwrites -----

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Method to get the Swiss oil balance data in tons."""
        url = "https://www.uvek-gis.admin.ch/BFE/ogd/124/ogd124_erd%C3%B6lbilanz.csv"
        df = pd.read_csv(url)

        data = df.set_index(["Energietraeger", "Rubrik", "Jahr"]).squeeze().unstack()
        data.index.names = ["element", "category"]

        return data

    # ------ Outward facing functions ------
    def get_kerosene_demand(self, year: int) -> float:
        """Get the demand for kerosene."""
        data = self.data.loc[("Flugpetrol", "Endverbrauch - Total"), year]
        energy_density = 43.2 / (
            Constants.GJ_PER_MWH * 1000
        )  # [GWh/t] https://www.bfe.admin.ch/bfe/de/home/versorgung/statistik-und-geodaten/energiestatistiken/gesamtenergiestatistik.exturl.html/aHR0cHM6Ly9wdWJkYi5iZmUuYWRtaW4uY2gvZGUvcHVibGljYX/Rpb24vZG93bmxvYWQvNzQ0Mg==.html
        data *= energy_density
        return data
