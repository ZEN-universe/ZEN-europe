from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.utils.constants import Constants


class MethanolProductionCollodi(Dataset[pd.Series]):
    """
    Dataset class for methanol production data from Collodi et al. (2017).

    """

    name = "methanol_production_collodi"
    MONEY_YEAR = 2014

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Demonstrating Large Scale Industrial CCS through CCU - A Case Study "
                "for Methanol Production"
            ),
            author=[
                "Guido Collodi",
                "Giuliana Azzaro",
                "Noemi Ferrari",
                "Stanley Santos",
            ],
            publication="Energy Procedia",
            publication_year=2017,
            url="https://www.sciencedirect.com/science/article/pii/S1876610217313280",
            doi="https://doi.org/10.1016/j.enconman.2021.115052",
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
    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """
        Get the lifetime for methanol from natural gas technologies.

        Returns:
            Attribute: An Attribute object containing the lifetime data.
        """

        attr = element.lifetime
        attr.set_data(
            default_value=25,
            source=SourceInformation(
                description=(
                    "The lifetime for methanol from natural gas technologies is based "
                    "on the work of Collodi et al. (2017)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_construction_time(self, element: ConversionTechnology) -> Attribute:
        """
        Get the construction time for methanol from natural gas technologies.

        Returns:
            Attribute: An Attribute object containing the construction time data.
        """

        attr = element.construction_time
        attr.set_data(
            default_value=3,
            source=SourceInformation(
                description=(
                    "The construction time for methanol from natural gas technologies "
                    "is based on the work of Collodi et al. (2017)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_conversion_factor(self, element: ConversionTechnology) -> Attribute:
        """
        Get the conversion factor for methanol from natural gas technologies.

        Returns:
            Attribute: An Attribute object containing the conversion factor data.
        """
        cf = [
            {"natural_gas": {"default_value": 1760 / 1163, "unit": "GWh/GWh"}},
            {"electricity": {"default_value": 18.47 / 1163, "unit": "GWh/GWh"}},
        ]
        attr = element.conversion_factor
        attr.set_data(
            default_value=cf,
            source=SourceInformation(
                description=(
                    "The conversion factor for methanol from natural gas technologies "
                    "is based on the work of Collodi et al. (2017)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def _calculate_hourly_methanol_production(self) -> float:
        """
        Calculate the methanol production in kW.

        Returns:
            float: Methanol production in kW.
        """
        methanol_production: float = 5000  # t/d
        methanol_production = (
            methanol_production
            / Constants.HOURS_PER_DAY
            * Constants.METHANOL_KWH_PER_KG
            * 1000
        )  # kW
        return methanol_production

    def get_capex_specific(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific capital expenditure (capex) for methanol from natural gas
        technologies.

        The total capex comes from Table 4
        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        attr = element.capex_specific_conversion
        capex_total = 693.7 * 1e6  # Euro
        methanol_production = self._calculate_hourly_methanol_production()
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        capex_specific = capex_total / methanol_production * inflation
        attr.set_data(
            default_value=capex_specific,
            unit="Euro/kW",
            source=SourceInformation(
                description=(
                    "The specific capex for methanol from natural gas technologies is "
                    "based on the work of Collodi et al. (2017)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific variable operational expenditure (opex) for methanol from
        natural gas technologies.

        The total opex comes from Table 5
        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        attr = element.opex_specific_variable
        opex_variable = 342042100  # Euro
        annual_production = (
            self._calculate_hourly_methanol_production() * Constants.HOURS_PER_YEAR
        ) / 1000  # MWh/year
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        opex_specific = opex_variable / annual_production * inflation
        attr.set_data(
            default_value=opex_specific,
            unit="Euro/MWh",
            source=SourceInformation(
                description=(
                    "The specific variable opex for methanol from natural gas "
                    "technologies is based on the work of Collodi et al. (2017)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_opex_specific_fixed(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific fixed operational expenditure (opex) for methanol from natural
        gas technologies.

        The total opex comes from Table 5
        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        attr = element.opex_specific_fixed
        opex_fixed = 26677400  # Euro
        methanol_production = self._calculate_hourly_methanol_production()
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        opex_specific = opex_fixed / methanol_production * inflation
        attr.set_data(
            default_value=opex_specific,
            unit="Euro/kW",
            source=SourceInformation(
                description=(
                    "The specific fixed opex for methanol from natural gas "
                    "technologies is based on the work of Collodi et al. (2017)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr
