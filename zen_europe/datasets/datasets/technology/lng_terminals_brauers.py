from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.utils.constants import Constants


class LNGTerminalsBrauers(Dataset[dict[str, pd.DataFrame]]):
    """
    LNG terminal dataset class from Brauers et al. (2021).

    Provides the lifetime of LNG terminals (p. 13) and their specific
    investment cost, derived from the cost and the capacity of the Brunsbuettel
    LNG terminal.
    """

    name = "lng_terminals_brauers"

    MONEY_YEAR = 2021
    LIFETIME = 30
    # cost and capacity of the Brunsbuettel LNG terminal
    CAPEX_TOTAL = 500e6  # Euro
    CAPACITY = 8  # bcm

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Liquefied natural gas expansion plans in Germany: "
                "The risk of gas lock-in under energy transitions"
            ),
            author=["Hanna Brauers", "Isabell Braunger", "Jessice Jewell"],
            publication="Energy Research & Social Science",
            publication_year=2021,
            doi="https://doi.org/10.1016/j.erss.2021.102059",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        """
        No data to be set.
        """
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    def get_lifetime(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the lifetime of LNG terminals.
        """
        attr = technology.lifetime
        return attr.set_data(
            default_value=self.LIFETIME,
            source=SourceInformation(
                description=(
                    f"The lifetime of {technology.name} is based on "
                    "Brauers et al. (2021) (p. 13)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capex_specific(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the specific investment cost of LNG terminals.
        """
        # convert the send-out capacity from bcm per year to kW
        capacity = (
            self.CAPACITY
            * Constants.NATURAL_GAS_GWH_PER_BCM
            / Constants.HOURS_PER_YEAR
            * 1e6
        )
        capex_specific = self.CAPEX_TOTAL / capacity  # Euro/kW
        inflation = ECBInflation(source_path=self.source_path)
        capex_specific = capex_specific * inflation.get_inflation_rate(
            self.MONEY_YEAR, technology.settings.time.price_year
        )
        attr = technology.capex_specific_conversion
        return attr.set_data(
            default_value=capex_specific,
            unit="Euro/kW",
            source=SourceInformation(
                description=(
                    f"The specific capital expenditure of {technology.name} is "
                    "based on the Brunsbuettel LNG terminal data of "
                    "Brauers et al. (2021)."
                ),
                metadata=self.metadata,
            ),
        )
