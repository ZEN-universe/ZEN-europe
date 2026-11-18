from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBInflation


class CO2StorageCostsZEP(Dataset[pd.Series]):
    """
    Dataset class for the costs of carbon storage based on the ZEP
    (Zero Emissions Platform) report.

    """

    name = "co2_storage_costs_zep"
    MONEY_YEAR = 2011

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("The Costs of CO2 Storage: Post-Demonstration CCS in the EU"),
            author=["ZEP", "ieaghg"],
            publication="ZEP",
            publication_year=2011,
            url="https://carbonmanagementeurope.org/publication/the-costs-of-co2-storage/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        data: dict[str, float] = {}
        return pd.Series(data)

    # -------- methods ------------------------
    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """
        Returns the lifetime from the ZEP carbon storage report.
        """
        attr = element.lifetime
        return attr.set_data(
            default_value=40,
            unit="1",
            source=SourceInformation(
                description=(
                    "The lifetime of carbon storage is based on the ZEP report "
                    "'The Costs of CO2 Storage: Post-Demonstration CCS in the EU'."
                    " (Table 4, Case 6, Medium)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """
        Returns the specific variable operational expenditure (opex) from the ZEP carbon
        storage report.
        """
        attr = element.opex_specific_variable
        opex = 4
        ecb_inflation = ECBInflation(source_path=self.source_path)
        inflation = ecb_inflation.get_inflation_rate(
            base_year=self.MONEY_YEAR,
            target_year=element.settings.time.price_year,
        )
        opex_data = opex * inflation
        return attr.set_data(
            default_value=opex_data,
            unit="Euro/tCO2",
            source=SourceInformation(
                description=(
                    "The variable opex of carbon storage is based on the ZEP report "
                    "'The Costs of CO2 Storage: Post-Demonstration CCS in the EU'."
                    " (Table 4, Case 6, Medium)."
                ),
                metadata=self.metadata,
            ),
        )
