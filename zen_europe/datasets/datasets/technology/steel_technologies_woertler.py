from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.utils.constants import Constants


class SteelTechnologiesWoertler(Dataset[pd.Series]):
    """
    Dataset class for the steel production technology from Woertler et al.

    """

    name = "steel_technologies_woertler"

    MONEY_YEAR = 2010

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Steel's contribution to a low-carbon Europe 2050: Technical and "
                "economic analysis of the sector's CO2 abatement potential"
            ),
            author=[
                "Martin Woertler",
                "Felix Schuler",
                "Nicole Voigt",
                "Torben Schmidt",
                "Peter Dahlmann",
                "Hans Bodo LÃ¼ngen",
                "Jean-Theo Ghenda",
            ],
            publication="Boston Consulting Group",
            publication_year=2013,
            url="https://www.stahl-online.de//wp-content/uploads/Schlussbericht-Studie-Low-carbon-Europe-2050_-Mai-20131.pdf",
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
        Get the specific capital expenditure (CAPEX) for steel production technologies.

        Returns:
            Attribute: An Attribute object containing the specific CAPEX data.
        """
        capex = {
            "BF_BOF": 170,
            "NG_DRI": 414,
            "H2_DRI": 414,
            "EAF": 184,
        }  # Euro/(tproduct/a), Exhibit 8
        assert element.name in capex, f"CAPEX data not available for {element.name}"
        specific_capex: float = capex[element.name]
        specific_capex *= Constants.HOURS_PER_YEAR  # Euro/(tproduct/h)
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        specific_capex *= inflation
        attr = element.capex_specific_conversion
        attr.set_data(
            default_value=specific_capex,
            unit="Euro/(tproduct/h)",
            source=SourceInformation(
                description=(
                    "The specific CAPEX for steel production technologies is derived "
                    "from Woertler et al. (2013) for the reference plant."
                ),
                metadata=self.metadata,
            ),
        )
        return attr
