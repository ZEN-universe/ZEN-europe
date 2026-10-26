from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.element import Element
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants

_MAP_TECHNOLOGY = {
    "Heizöl": "oil_boiler",
    "Erdgas": "natural_gas_boiler",
    "Holz": "biomass_boiler",
    "El. Widerstandsheizungen": "electrode_boiler",
    "Fernwärme": "district_heating_grid",
    "El. Ohm'sche Anlagen": "electrode_boiler",
}


class BFE(Dataset[dict[str, pd.DataFrame]]):
    """
    Bundesamt für Energie (BFE) dataset class.

    This class implements the specific behavior for the BFE dataset.
    """

    name = "bfe"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Energieverbrauch nach Verwendungszweck"),
            author=["Bundesamt für Energie (BFE)"],
            publication="BFE",
            publication_year=2025,
            url="https://www.bfe.admin.ch/bfe/de/home/versorgung/statistik-und-geodaten/energiestatistiken/energieverbrauch-nach-verwendungszweck.html",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path / "02-carrier" / "heat" / "12361-VWZ_Webtabellen_2024.xlsx"
        )

    def _set_data(self) -> dict[str, pd.DataFrame]:
        data_res = pd.read_excel(
            self.path, sheet_name="Tabelle17", skiprows=5, usecols="B:AA"
        )
        data_ser = pd.read_excel(
            self.path, sheet_name="Tabelle26", skiprows=5, usecols="B:AA"
        )
        data_res_space_split = pd.read_excel(
            self.path, sheet_name="Tabelle20", skiprows=5, usecols="B:AA"
        )
        data_res_water_split = pd.read_excel(
            self.path, sheet_name="Tabelle22", skiprows=5, usecols="B:AA"
        )
        data_res = (
            data_res.set_index("Verwendungszweck") / Constants.GJ_PER_MWH * 1000
        )  # from PJ to GWh
        data_ser = (
            data_ser.set_index("Verwendungszweck") / Constants.GJ_PER_MWH * 1000
        )  # from PJ to GWh
        data_res_space_split = (
            data_res_space_split.set_index("Anlagensystem")
            / Constants.GJ_PER_MWH
            * 1000
        )  # from PJ to GWh
        data_res_water_split = (
            data_res_water_split.set_index("Anlagensystem")
            / Constants.GJ_PER_MWH
            * 1000
        )  # from PJ to GWh
        return {
            "residential": data_res.sort_index(),
            "service": data_ser.sort_index(),
            "residential_space_split": data_res_space_split.sort_index(),
            "residential_water_split": data_res_water_split.sort_index(),
        }

    # -------- methods ------------------------
    def get_demand(self, element: Element) -> pd.Series:
        """
        Get the CH heat demand.

        Args:
            element (Element): The element for which to get the demand.
        """
        time_series_year = element.model.settings.time.time_series_year
        data_res = self.data["residential"].loc[
            ["Raumwärme", "Warmwasser"], time_series_year
        ]
        data_ser = self.data["service"].loc[
            ["Raumwärme", "Warmwasser"], time_series_year
        ]
        data_res = data_res.rename(
            {"Raumwärme": "space_heating", "Warmwasser": "water_heating"}
        )
        data_ser = data_ser.rename(
            {"Raumwärme": "space_heating", "Warmwasser": "water_heating"}
        )
        data = pd.concat({"residential": data_res, "tertiary": data_ser})
        return data

    def get_share_household(self) -> pd.DataFrame:
        """
        Get the split of household heat demand into technology categories.
        """
        space_split = self.data["residential_space_split"].rename(index=_MAP_TECHNOLOGY)
        water_split = self.data["residential_water_split"].rename(index=_MAP_TECHNOLOGY)
        space_split.loc["heat_pump"] = (
            space_split.loc["El. Wärmepumpen ¹⁾"] + space_split.loc["Umweltwärme"]
        )
        water_split.loc["heat_pump"] = (
            water_split.loc["El. Wärmepumpen"] + water_split.loc["Umweltwärme"]
        )
        selected_technologies = list(set(_MAP_TECHNOLOGY.values())) + ["heat_pump"]
        space_split = space_split.loc[selected_technologies]
        water_split = water_split.loc[selected_technologies]
        total = space_split + water_split
        share = total.div(total.sum())
        share = share.sort_index()
        share.index.name = "technology"
        share.columns = share.columns.astype(int)
        return share
