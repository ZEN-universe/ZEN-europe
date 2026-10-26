from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.financial.ECB import ECBInflation

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants


class ShippingTechnologiesKorberg(Dataset[dict[str, pd.DataFrame]]):
    """
    Shipping technologies dataset class from Korberg et al. (2021).

    This class implements the specific behavior for the Shipping Technologies dataset.
    """

    name = "shipping_technologies_korberg"

    MONEY_YEAR = 2021

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation().get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Techno-economic assessment of advanced fuels and propulsion systems "
                "in future fossil-free ships"
            ),
            author=["A.D. Korberg", "S. Brynolf", "M. Grahn", "I.R. Skov"],
            publication="Renewable and Sustainable Energy Reviews",
            publication_year=2021,
            url="https://www.sciencedirect.com/science/article/pii/S1364032121001556",
            doi="https://doi.org/10.1016/j.rser.2021.110861",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        # TODO there is no data to be implemented
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    def get_shipping_conversion_factors(
        self, technology: ConversionTechnology | str
    ) -> dict[str, float]:
        """
        Get the shipping conversion factors for a specific technology.

        This method retrieves the conversion factors for the specified shipping
        technology
        and returns them as a dictionary.

        Returns:
            A dictionary containing the conversion factors for the specified technology.
        """
        if isinstance(technology, ConversionTechnology):
            technology = technology.name
        electricity_demand_LH2 = 6.78  # kWh/kg, https://www.sciencedirect.com/science/article/pii/S0306261917305457
        conversion_factors = {
            "diesel_ICE_ship": {"diesel": 1 / 0.45},
            "hydrogen_FC_ship": {
                "hydrogen": 1 / 0.55,
                "electricity": (
                    1 / 0.55 * electricity_demand_LH2 / Constants.HYDROGEN_KWH_PER_KG
                ),
            },
            "methanol_ICE_ship": {"methanol": 1 / 0.45},
            "ammonia_ICE_ship": {"ammonia": 1 / 0.45},
        }
        if technology not in conversion_factors:
            raise ValueError(
                f"Conversion factors for technology"
                f"'{technology}' are not available."
            )
        return conversion_factors[technology]

    def get_lifetime(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the lifetime of a specific shipping technology.

        This method retrieves the lifetime for the specified shipping technology
        and returns it as an Attribute.

        Returns:
            An Attribute object representing the lifetime of the specified technology in
            years.
        """
        lifetimes = {
            "diesel_ICE_ship": 30,
            "hydrogen_FC_ship": 15,
            "methanol_ICE_ship": 30,
            "ammonia_ICE_ship": 30,
        }
        if technology.name not in lifetimes:
            raise ValueError(
                f"Lifetime for technology '{technology.name}' is not available."
            )
        default_value = lifetimes[technology.name]
        attr = technology.lifetime
        attr.set_data(
            default_value=default_value,
            source=SourceInformation(
                description=(
                    f"The lifetime of {technology.name} is based on Korberg et al. "
                    "(2021)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_fuel_distribution_cost(self, technology: ConversionTechnology) -> float:
        """
        Get the fuel distribution cost for a specific shipping technology.

        This method retrieves the fuel distribution cost for the specified shipping
        technology
        and returns it as a float.

        Returns:
            A float representing the fuel distribution cost of the specified technology
            in Euro/GJ.
        """
        fuel_distribution_costs = {
            "diesel_ICE_ship": 0.2,
            "hydrogen_FC_ship": 11.6,
            "methanol_ICE_ship": 0.6,
            "ammonia_ICE_ship": 1.2,
        }
        if technology.name not in fuel_distribution_costs:
            raise ValueError(
                f"Fuel distribution cost for technology '{technology.name}' "
                "is not available."
            )
        inflation = self.get_inflation_rate(
            base_year=self.MONEY_YEAR,
            target_year=technology.settings.time.price_year,
        )
        return fuel_distribution_costs[technology.name] * inflation

    def get_capex_specific(self, technology: ConversionTechnology) -> tuple[float, str]:
        """
        Get the specific capital expenditure (capex) for a specific shipping technology.

        This method retrieves the specific capex for the specified shipping technology
        and returns it as a float.

        Returns:
            A float representing the specific capex of the specified technology in
            Euro/kW.
        """
        specific_capex_values = {
            "diesel_ICE_ship": 460,
            "hydrogen_FC_ship": 505,
            "methanol_ICE_ship": 600,
            "ammonia_ICE_ship": 730,
        }
        selected_technologies = {
            "diesel_ICE_ship": "ICE diesel two-stroke",
            "hydrogen_FC_ship": "Fuel cell hydrogen",
            "methanol_ICE_ship": "ICE methanol two-stroke",
            "ammonia_ICE_ship": "ICE ammonia two-stroke",
        }
        if technology.name not in specific_capex_values:
            raise ValueError(
                f"Specific capex for technology '{technology.name}' is not available."
            )

        inflation = self.get_inflation_rate(
            base_year=self.MONEY_YEAR,
            target_year=technology.settings.time.price_year,
        )
        return (
            specific_capex_values[technology.name] * inflation,
            selected_technologies[technology.name],
        )

    def get_opex_fixed(self, technology: ConversionTechnology) -> float:
        """
        Get the fixed operational expenditure (opex) for a specific shipping technology.

        This method retrieves the fixed opex for the specified shipping technology
        and returns it as a float.

        Returns:
            A float representing the fixed opex of the specified technology in Euro/kW.
        """
        fixed_opex_values = {
            "diesel_ICE_ship": 0.025,
            "hydrogen_FC_ship": 0.026,
            "methanol_ICE_ship": 0.025,
            "ammonia_ICE_ship": 0.04,
        }
        if technology.name not in fixed_opex_values:
            raise ValueError(
                f"Fixed opex for technology '{technology.name}' is not available."
            )
        capex = self.get_capex_specific(technology)[0]
        return fixed_opex_values[technology.name] * capex

    def get_max_load(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the maximum load for a specific shipping technology.

        This method retrieves the maximum load for the specified shipping technology
        and returns it as an Attribute.

        Returns:
            An Attribute object representing the maximum load of the specified
            technology.
        """
        max_loads = {
            "diesel_ICE_ship": 0.75 * 5280 / Constants.HOURS_PER_YEAR,
            "hydrogen_FC_ship": 0.75 * 5280 / Constants.HOURS_PER_YEAR,
            "methanol_ICE_ship": 0.75 * 5280 / Constants.HOURS_PER_YEAR,
            "ammonia_ICE_ship": 0.75 * 5280 / Constants.HOURS_PER_YEAR,
        }
        if technology.name not in max_loads:
            raise ValueError(
                f"Maximum load for technology '{technology.name}' is not available."
            )
        default_value = max_loads[technology.name]
        attr = technology.max_load
        attr.set_data(
            default_value=default_value,
            source=SourceInformation(
                description=(
                    f"The maximum load of {technology.name} is "
                    "based on Korberg et al. (2021)."
                    " Ships are assumed to operate at 75% of nominal capacity "
                    "for 5280 hours per year."
                ),
                metadata=self.metadata,
            ),
        )
        return attr
