from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.element import Element
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants

_KTOE2GWH = 1 / Constants.TOE_PER_MWH  # ktoe (useful energy) -> GWh


class DESNZ(Dataset[pd.DataFrame]):
    """
    Department for Energy Security and Net Zero dataset class.

    This class implements the specific behavior for the DESNZ dataset.
    """

    name = "desnz"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Energy Consumption in the UK (ECUK): End Use Tables"),
            author=["Department for Energy Security and Net Zero (DESNZ)"],
            publication="DESNZ",
            publication_year=2025,
            url="https://www.gov.uk/government/statistics/energy-consumption-in-the-uk-2025",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "heat"

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_excel(
            self.path / "ECUK_2025_End_Use_tables_200426.xlsx",
            sheet_name="Table U2",
            skiprows=2,
        )
        data = data.set_index(["Sector", "End use", "Year"]) * _KTOE2GWH
        return data.sort_index()

    # -------- methods ------------------------
    def get_service_demand(self, element: Element) -> pd.Series:
        """
        Get the UK heat demand for the Service sector.

        Args:
            element (Element): The element for which to get the demand.
        """
        time_series_year = element.model.settings.time.time_series_year
        data_ser = cast(pd.Series, self.data.loc["Services", "Total"])
        data_ser = data_ser.loc[["Space heating ", "Water heating "]]
        data_ser = data_ser.xs(time_series_year, level="Year")
        data_ser = data_ser.rename(
            index={"Space heating ": "space_heating", "Water heating ": "water_heating"}
        )
        return data_ser
