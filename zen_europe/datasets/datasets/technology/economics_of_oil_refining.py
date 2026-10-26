from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.utils.constants import Constants


class EconomicsOfOilRefining(Dataset[pd.Series]):
    """
    Dataset class for the economics of oil refining.

    """

    name = "economics_of_oil_refining"

    MONEY_YEAR = 2022

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Economics of oil refining for net-zero hydrogen supply chains"),
            author=["Jean-Pierre Favennec"],
            publication="The Palgrave Handbook of International Energy Economics",
            publication_year=2022,
            url="https://link.springer.com/chapter/10.1007/978-3-030-86884-0_3",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        data: dict[str, float] = {}
        return pd.Series(data)

    # -------- methods ------------------------
    def get_capex_specific(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific capital expenditure for refining technologies.

        6 bn USD for 8 mn tons/year, 8760 hours per year

        Returns:
            Attribute: An Attribute object containing the specific capital expenditure
                data.
        """
        attr = element.capex_specific_conversion
        total_capex = 6 * 1e9  # 6 billion USD
        total_capacity = 8 * 1e6  # 8 million tons/year
        specific_capex = total_capex / (
            total_capacity * Constants.HOURS_PER_YEAR
        )  # USD/(t/h)
        ecb_d2e = ECBDollar2Euro()
        d2e = ecb_d2e.get_dollar2euro(self.MONEY_YEAR)
        inflation = ECBInflation()
        inflation_factor = inflation.get_inflation_rate(
            self.MONEY_YEAR, element.settings.time.price_year
        )
        specific_capex = specific_capex * d2e * inflation_factor * Constants.TOE_PER_MWH
        attr.set_data(
            default_value=specific_capex,
            source=SourceInformation(
                description=(
                    "The specific capital expenditure for refining technologies is "
                    "obtained from the economics of oil refining dataset."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/MW",
        )
        return attr

    def get_opex_specific_fixed(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific fixed operational expenditure for refining technologies.

        1-2% of capex for maintenance, 15-40 million USD for labor

        Returns:
            Attribute: An Attribute object containing the specific fixed operational
                expenditure data.
        """
        attr = element.opex_specific_fixed
        opex_maintenance = (
            0.015 * 6 * 1e9
        )  # 1-2% of capex for maintenance, 1.5% assumed
        opex_labor = 27.5 * 1e6  # 15-40 million USD for labor, 27.5 million USD assumed
        total_opex = opex_maintenance + opex_labor
        total_capacity = 8 * 1e6  # 8 million tons/year
        specific_opex = total_opex / (
            total_capacity * Constants.HOURS_PER_YEAR
        )  # USD/(t/h)
        ecb_d2e = ECBDollar2Euro()
        d2e = ecb_d2e.get_dollar2euro(self.MONEY_YEAR)
        inflation = ECBInflation()
        inflation_factor = inflation.get_inflation_rate(
            self.MONEY_YEAR, element.settings.time.price_year
        )
        specific_opex = specific_opex * d2e * inflation_factor * Constants.TOE_PER_MWH
        attr.set_data(
            default_value=specific_opex,
            source=SourceInformation(
                description=(
                    "The specific fixed operational expenditure for refining "
                    "technologies is obtained from the economics of oil refining "
                    "dataset."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/MW",
        )
        return attr

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific variable operational expenditure for refining technologies.

        $1 per barrel
        Returns:
            Attribute: An Attribute object containing the specific variable operational
                expenditure data.
        """
        attr = element.opex_specific_variable
        opex_variable = 1  # 1 USD per barrel
        specific_opex = opex_variable * Constants.BARREL_PER_TON  # USD per ton
        ecb_d2e = ECBDollar2Euro()
        d2e = ecb_d2e.get_dollar2euro(self.MONEY_YEAR)
        inflation = ECBInflation()
        inflation_factor = inflation.get_inflation_rate(
            self.MONEY_YEAR, element.settings.time.price_year
        )
        specific_opex = specific_opex * d2e * inflation_factor * Constants.TOE_PER_MWH
        attr.set_data(
            default_value=specific_opex,
            source=SourceInformation(
                description=(
                    "The specific variable operational expenditure for refining "
                    "technologies is obtained from the economics of oil refining "
                    "dataset."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/MWh",
        )
        return attr
