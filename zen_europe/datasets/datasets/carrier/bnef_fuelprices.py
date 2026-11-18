from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.carriers.carrier import Carrier
    from zen_creator.elements.element import Element
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute, SourceInformation

from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation


class BNEFFuelPrices(Dataset[pd.DataFrame]):
    """
    BNEF Fuel Prices dataset class.

    This class implements the specific behavior for the BNEF dataset.
    """

    name = "bnef_fuel_prices"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("1H 2022 LCOE Update - Charts"),
            author=["BloombergNEF"],
            publication="BloombergNEF",
            publication_year=2022,
            url="https://about.bnef.com/insights/commodities/2h-2022-levelized-cost-of-electricity-update/",
            note=(
                "Link is for the 2H 2022 update, but the data is from the 1H 2022 "
                "update; original link to the 1H 2022 update is no longer available."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "fuel_prices"

    def _set_data(self) -> pd.DataFrame:
        df = pd.read_excel(
            self.path / "2022-10-06 - 1H 2022 LCOE Update.xlsx",
            sheet_name="Manual Values MWh",
        ).set_index("element")

        return df

    # -------- methods ------------------------
    def get_price_import(
        self, element: Carrier, manual_carrier_name: str | None = None
    ) -> Attribute:
        """
        Get the import price of a carrier.

        This function retrieves the import price data for the specified carrier.
        Args:
            element (Carrier): The carrier element for which to retrieve the import
                price.
            manual_carrier_name (str, optional): If provided, this name will be used
                to look up the price data
                instead of the element's name. Defaults to None.
        Returns:
            Attribute: An Attribute object containing the import price data for the
                carrier.
        """
        data = self.get_price_import_data(element, manual_carrier_name)
        df = cast(float, data.loc[element.settings.time.reference_year])
        yearly_variations_df = data / df
        yearly_variations_df.index.name = "year"
        yearly_variations_df.name = "price_import"
        source = SourceInformation(
            description=(
                "Carrier import price data is derived from the BloombergNEF LCOE "
                "dataset. The data is provided in $/MWh (2021 real) and is converted "
                "to Euro/MWh using the ECB dollar-to-euro exchange rate and inflation "
                "rate."
            ),
            metadata=self.metadata,
        )
        return element.price_import.set_data(
            default_value=df,
            yearly_variations_df=yearly_variations_df,
            unit="Euro/MWh",
            source=source,
        )

    def get_price_import_data(
        self, element: Element, manual_carrier_name: str | None = None
    ) -> pd.Series:
        """
        Get the import price data of one carrier.

        Returns:
            pd.Series: The import price per year in Euro/MWh.
        """
        if manual_carrier_name:
            data = cast(pd.Series, self.data.loc[manual_carrier_name])
        else:
            data = cast(pd.Series, self.data.loc[element.name])
        unit = data.loc["Unit new"]
        assert unit == "$/MWh (2021 real)", (
            f"Unexpected unit for" f"BNEF carrier prices: {unit}"
        )
        common_years = data.index.intersection(element.settings.time.years)
        data = data.loc[common_years]
        data.index = data.index.astype(int)
        dollar_to_euro = ECBDollar2Euro(source_path=self.source_path).get_dollar2euro(
            year=2021
        )
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=2021, target_year=element.settings.time.price_year
        )
        data = data * dollar_to_euro * inflation
        return data
