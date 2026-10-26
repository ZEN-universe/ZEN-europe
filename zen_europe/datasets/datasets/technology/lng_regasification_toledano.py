from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation


class LNGRegasificationToledano(Dataset[dict[str, pd.DataFrame]]):
    """
    LNG regasification cost dataset class from Toledano et al. (2018).

    Provides the regasification cost of LNG terminals, converted from
    dollar per MMBtu to Euro per MWh.
    """

    name = "lng_regasification_toledano"

    MONEY_YEAR = 2018
    REGASIFICATION_COST = 0.5  # dollar/MMBtu
    MWH_PER_MMBTU = 0.293

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="The Open LNG Regasification Model: A Manual",
            author=[
                "Perrine Toledano",
                "Nicolas Maennling",
                "Thomas Mitro",
                "Felipe Botelho Tavares",
            ],
            publication="CCSI",
            publication_year=2018,
            url=(
                "https://www.researchgate.net/publication/"
                "329641146_Manual_for_the_Open_LNG_Regasification_Model"
            ),
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
    def get_opex_specific_variable(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the variable operational cost of LNG terminals.
        """
        vopex = self.REGASIFICATION_COST / self.MWH_PER_MMBTU  # dollar/MWh
        ecb_dollar2euro = ECBDollar2Euro(source_path=self.source_path)
        vopex = vopex * ecb_dollar2euro.get_dollar2euro(self.MONEY_YEAR)
        inflation = ECBInflation(source_path=self.source_path)
        vopex = vopex * inflation.get_inflation_rate(
            self.MONEY_YEAR, technology.settings.time.price_year
        )
        attr = technology.opex_specific_variable
        return attr.set_data(
            default_value=vopex,
            unit="Euro/MWh",
            source=SourceInformation(
                description=(
                    f"The variable opex of {technology.name} is set to the "
                    f"regasification cost of {self.REGASIFICATION_COST} "
                    "dollar per MMBtu of Toledano et al. (2018), converted to "
                    "Euro per MWh."
                ),
                metadata=self.metadata,
            ),
        )
