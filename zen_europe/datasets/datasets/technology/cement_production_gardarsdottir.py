from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.financial.ECB import ECBInflation


class CementProductionGardarsdottir(Dataset[pd.Series]):
    """
    Dataset class for the cement production technology from Gardarsdottir et al. (2021).

    """

    name = "cement_production_gardarsdottir"

    MONEY_YEAR = 2014

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Comparison of Technologies for CO2 Capture from Cement "
                "Productionâ€”Part 2: Cost Analysis"
            ),
            author=[
                "Stefania Osk Gardarsdottir",
                "Edoardo De Lena",
                "Matteo Romano",
                "Simon Roussanaly",
                "Mari Voldsund",
                "JosÃ©-Francisco PÃ©rez-Calvo",
                "David Berstad",
                "Chao Fu",
                "Rahul Anantharaman",
                "Daniel Sutter",
                "Matteo Gazzani",
                "Marco Mazzotti",
                "Giovanni Cinti",
            ],
            publication="MDPI Energies",
            publication_year=2019,
            url="https://www.mdpi.com/1996-1073/12/3/542",
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
    def _get_capex_production_value(self) -> tuple[float, float]:
        """
        Get the total CAPEX and the hourly production of cement production.

        Returns:
            The total CAPEX in Euro and the hourly production in t/h.
        """
        capex_total = 204 * 1e6  # Euro, Table 6
        hourly_production = 120.65  # t/h, Table 1
        return capex_total, hourly_production

    def get_capex_specific(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific capital expenditure (CAPEX) for cement kilns.

        Returns:
            Attribute: An Attribute object containing the specific CAPEX data.
        """
        attr = element.capex_specific_conversion
        capex_total, hourly_production = self._get_capex_production_value()
        specific_capex = capex_total / hourly_production

        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        specific_capex *= inflation
        attr.set_data(
            default_value=specific_capex,
            source=SourceInformation(
                description=(
                    "The specific CAPEX for cement kilns is derived from "
                    "Gardarsdottir et al. (2019) for the reference plant."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/(tproduct/h)",
        )
        return attr

    def get_opex_specific_fixed(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific fixed operational expenditure (OPEX) for cement kilns.

        Returns:
            Attribute: An Attribute object containing the specific fixed OPEX data.
        """
        attr = element.opex_specific_fixed
        capex_total, hourly_production = self._get_capex_production_value()
        share_of_capex = 0.025 + 0.02  # for maintenance and insurance, p. 8
        labor_cost = 100 * 60000  # Euro/year, p. 8, 100 employees with 60k Euro/year
        opex_total = share_of_capex * capex_total + labor_cost  # Euro/year
        opex_specific_fixed = opex_total / hourly_production

        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        opex_specific_fixed *= inflation
        attr.set_data(
            default_value=opex_specific_fixed,
            source=SourceInformation(
                description=(
                    "The specific fixed OPEX for cement kilns is derived from "
                    "Gardarsdottir et al. (2019) for the reference plant."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/(tproduct/h)",
        )
        return attr

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific variable operational expenditure (OPEX) for cement kilns.

        Returns:
            Attribute: An Attribute object containing the specific variable OPEX data.
        """
        attr = element.opex_specific_variable
        opex_specific_variable = 6.875  # Euro/tproduct, screengrab from Fig. 4
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        opex_specific_variable *= inflation
        attr.set_data(
            default_value=opex_specific_variable,
            source=SourceInformation(
                description=(
                    "The specific variable OPEX for cement kilns is derived from "
                    "Gardarsdottir et al. (2019) for the reference plant."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/tproduct",
        )
        return attr

    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """
        Get the lifetime for cement kilns.

        Returns:
            Attribute: An Attribute object containing the lifetime data.
        """
        attr = element.lifetime
        lifetime = 25  # years, Table 5

        attr.set_data(
            default_value=lifetime,
            source=SourceInformation(
                description=(
                    "The life time for cement kilns is derived from "
                    "Gardarsdottir et al. (2019) for the reference plant."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )
        return attr

    def get_construction_time(self, element: ConversionTechnology) -> Attribute:
        """
        Get the construction time for cement kilns.

        Returns:
            Attribute: An Attribute object containing the construction time data.
        """
        attr = element.construction_time
        construction_time = 2  # years, Table 5

        attr.set_data(
            default_value=construction_time,
            source=SourceInformation(
                description=(
                    "The construction time for cement kilns is derived from "
                    "Gardarsdottir et al. (2019) for the reference plant."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )
        return attr
