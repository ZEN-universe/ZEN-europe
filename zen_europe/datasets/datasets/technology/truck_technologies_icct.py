from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.utils.utils import interpolate_missing_years

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants


class TruckTechnologiesICCT(Dataset[dict[str, pd.DataFrame]]):
    """
    Truck technologies dataset class from ICCT (2023).

    This class implements the specific behavior for the Truck Technologies dataset.

    The selected truck model is 5-LH (500km), because it is the most representative
    model for the European truck fleet.
    """

    name = "truck_technologies_icct"

    PAYLOAD = 13842 / 1000  # t, Tab A18
    ANNUAL_MILEAGE = 116000  # km, Tab 6
    LIFETIME_MILEAGE = 1400000  # km, Tab 6
    HOURLY_TONNE_MILEAGE = ANNUAL_MILEAGE / 8760 * PAYLOAD  # tkm/h, Tab 6
    MONEY_YEAR = 2022

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation().get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "THE EUROPEAN HEAVY-DUTY VEHICLE MARKET UNTIL 2040: ANALYSIS OF "
                "DECARBONIZATION PATHWAYS"
            ),
            author=["Hussein Basma", "Felipe Rodriguez"],
            publication="International Council on Clean Transportation (ICCT)",
            publication_year=2023,
            url="https://theicct.org/wp-content/uploads/2023/01/hdv-europe-decarb-costs-jan23.pdf",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        # TODO there is no data to be implemented
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """
        Get the lifetime of the specified conversion technology element.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the lifetime.

        Returns:
            Attribute: An Attribute object containing the lifetime of the specified
                conversion technology element.
        """
        attr = element.lifetime
        return attr.set_data(
            default_value=round(self.LIFETIME_MILEAGE / self.ANNUAL_MILEAGE),
            source=SourceInformation(
                description=(
                    f"The lifetime of {element.name} is "
                    "sourced from the ICCT (2023) dataset for the 5-LH truck model. It "
                    "is obtained by dividing the total mileage of the truck by the "
                    "average annual mileage (Tab 6)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_conversion_factor(self, element: ConversionTechnology) -> Attribute:
        """
        Get the conversion factor of the specified conversion technology element.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the conversion factor.

        Returns:
            Attribute: An Attribute object containing the conversion factor of the
                specified conversion technology element.
        """
        # one entry per input carrier, as expected by the conversion_factor
        # attribute
        conversion_factors = {
            "HDT_BET": [
                {
                    "electricity": {
                        "default_value": 1.24 / self.PAYLOAD,
                        "unit": "kWh/tkm",
                    }
                }
            ],
            "HDT_FCEV": [
                {
                    "hydrogen": {
                        "default_value": 7.87
                        * Constants.HYDROGEN_KWH_PER_KG
                        / 100
                        / self.PAYLOAD,
                        "unit": "kWh/tkm",
                    }
                }
            ],
            "HDT_diesel": [
                {
                    "diesel": {
                        "default_value": 34.42
                        * Constants.DIESEL_KWH_PER_LITER
                        / 100
                        / self.PAYLOAD,
                        "unit": "kWh/tkm",
                    }
                }
            ],
        }
        source_tables = {
            "HDT_BET": "Tab A9",
            "HDT_FCEV": "Tab A9",
            "HDT_diesel": "Tab A6",
        }
        if element.name not in conversion_factors:
            raise ValueError(f"Conversion factor for {element.name} is not defined.")

        attr = element.conversion_factor
        return attr.set_data(
            default_value=conversion_factors[element.name],
            source=SourceInformation(
                description=(
                    f"The conversion factor of {element.name} is "
                    "sourced from the ICCT (2023) dataset for the 5-LH truck model. "
                    f"It is obtained from {source_tables[element.name]} of the dataset."
                ),
                metadata=self.metadata,
            ),
        )

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific variable operational expenditure (OPEX) of the specified
        conversion technology element.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the specific variable OPEX.

        Returns:
            Attribute: An Attribute object containing the specific variable OPEX of the
                specified conversion technology element.
        """
        opex_specific_variable = {
            "HDT_BET": 13.24 / 100 / self.PAYLOAD,
            "HDT_FCEV": 13.78 / 100 / self.PAYLOAD,
            "HDT_diesel": 18.5 / 100 / self.PAYLOAD,
        }
        if element.name not in opex_specific_variable:
            raise ValueError(
                f"Specific variable OPEX for {element.name} is not defined."
            )
        data = opex_specific_variable[element.name]
        inflation = self.get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        data = data * inflation
        attr = element.opex_specific_variable
        return attr.set_data(
            default_value=data,
            source=SourceInformation(
                description=(
                    f"The specific variable OPEX of {element.name} is "
                    "sourced from the ICCT (2023) dataset for the 5-LH truck model "
                    "(Tab A20). "
                ),
                metadata=self.metadata,
            ),
            unit="Euro/tkm",
        )

    def get_capex_specific_conversion(
        self, element: ConversionTechnology
    ) -> tuple[pd.Series, str]:
        """
        Get the specific conversion capital expenditure (CAPEX) of the specified
        conversion technology element.

        Args:
            element (ConversionTechnology): The conversion technology element for which
                to get the specific conversion CAPEX.

        Returns:
            Attribute: An Attribute object containing the specific conversion CAPEX of
                the specified conversion technology element.
        """
        capex_specific_conversion = {
            "HDT_BET": {2022: 205539, 2030: 116909, 2040: 95044},
            "HDT_FCEV": {2022: 235626, 2030: 141940, 2040: 108830},
            "HDT_diesel": {2022: 84600, 2030: 84600, 2040: 84600},
        }
        sources = {
            "HDT_BET": "Fig. 8",
            "HDT_FCEV": "Fig. 9",
            "HDT_diesel": "Tab A15",
        }
        if element.name not in capex_specific_conversion:
            raise ValueError(
                f"Specific conversion CAPEX for {element.name} is not defined."
            )
        data = pd.Series(capex_specific_conversion[element.name], dtype=float)
        data = interpolate_missing_years(data)
        data = data / self.HOURLY_TONNE_MILEAGE
        inflation = self.get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        data = data * inflation
        data.index.name = "year"
        data.name = "capex_specific_conversion"
        return data, sources[element.name]
