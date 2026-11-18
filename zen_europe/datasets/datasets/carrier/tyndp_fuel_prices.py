from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import Attribute, Carrier
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.utils.constants import Constants


class TYNDPFuelPrices(Dataset[pd.Series]):
    """
    Fuel prices dataset for the TYNDP (Ten-Year Network Development Plan).

    This class implements the specific behavior for the TYNDP fuel prices dataset.
    """

    name = "tyndp_fuel_prices"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Fuel Commodities and Carbon Prices"),
            author=["ENTSO-E", "ENTSOG"],
            publication="TYNDP 2020 Scenario Report",
            publication_year=2020,
            url="https://2020.entsos-tyndp-scenarios.eu/fuel-commodities-and-carbon-prices/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the manual data for the TYNDP fuel prices dataset in €/GJ in 2020."""
        return pd.Series({"uranium": 0.47, "lignite": 1.1})

    # -------- methods ------------------------
    def get_price_import(self, element: Carrier) -> Attribute:
        """
        Get the import price of a specific element.

        Args:
            element: The element for which to get the price.

        Returns:
            Attribute: The import price attribute of the element in €/MWh.
        """
        if element.name not in self.data.index:
            raise ValueError(
                f"Fuel price for {element.name}"
                "is not available in the TYNDP 2020 dataset."
            )
        default_value = (
            cast(float, self.data.loc[element.name]) * Constants.GJ_PER_MWH
        )  # convert from €/GJ to €/MWh
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=2020, target_year=element.settings.time.price_year
        )
        source = SourceInformation(
            description=(
                f"Import price of {element.name} from the TYNDP 2020 dataset, "
                "converted from €/GJ to €/MWh and adjusted for inflation."
            ),
            metadata=self.metadata,
        )
        return element.price_import.set_data(
            source=source,
            default_value=default_value * inflation,  # apply inflation adjustment
            unit="Euro/MWh",
        )
