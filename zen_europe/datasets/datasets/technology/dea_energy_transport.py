from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, SourceInformation, TransportTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBInflation


class DEAEnergyTransport(Dataset[dict[str, pd.DataFrame]]):
    """
    Energy transport dataset class from the technology catalogue for energy
    transport of the Danish Energy Agency.

    Hydrogen pipelines: from the data sheet of the main
    hydrogen distribution line (70 bar).
    Natural gas pipelines: from the data sheet of the
    main natural gas distribution line (500-1000 MW).
    Power lines: Overhead AC lines,

    The costs for hydrogen pipelines are not extracted from the data sheet,
    but from other data sources

    All distance-specific costs are reported in Euro per MW and km, in the
    MONEY_YEARS Euro of the technology, and are corrected for inflation in the
    getters.

    """

    name = "dea_energy_transport"

    # the index sheet of the catalogue states that the cost data for electricity
    # transmission, district heating, hydrogen pipelines and road is in 2025 Euro
    MONEY_YEARS = {
        "power_line": 2025,
        "hydrogen_pipeline": 2025,
        "natural_gas_pipeline": 2020,
    }

    COST_PER_DISTANCE_UNIT = "Euro/MW/km"
    HYDROGEN_PIPELINE_CAPACITY = 1.2  # GW for a 12 inch line at 90 bar
    LIFETIMES = {
        "hydrogen_pipeline": 50,
        "natural_gas_pipeline": 50,
        "power_line": 40,
    }
    # transport losses per km, converted to losses per km in the getter
    TRANSPORT_LOSSES_PER_KM = {
        "hydrogen_pipeline": 1.9 / 100 / 100,  # 1.9% per 100 km
        "natural_gas_pipeline": 0.1 / 100,  # 0.1% per km
        "power_line": 5 / 100 / 100,  # 5% per 100 km
    }
    CONSTRUCTION_TIMES = {
        "hydrogen_pipeline": 2,
        "natural_gas_pipeline": 1,
        "power_line": 3,
    }
    CAPEX_PER_DISTANCE = {
        # 0.7 Euro/MW/m -> 700 Euro/MW/km for a 500-1000 MW line
        "natural_gas_pipeline": 0.7 * 1000,
        # 0.75 kiloEuro/MW/km -> 750 Euro/MW/km for a 1000 MW line
        "power_line": 0.75 * 1000,
    }
    OPEX_FIXED_PER_DISTANCE = {
        # Euro/MW/km for a 500-1000 MW line # TODO seems low, check again
        "natural_gas_pipeline": 0.13,
        # 1.5% of the capex
        "power_line": CAPEX_PER_DISTANCE["power_line"] * 0.015,
    }
    SOURCE_SHEET = {
        "hydrogen_pipeline": "Pipeline transp. 90 bar (12 inch line)",
        "natural_gas_pipeline": "gas Main distri line",
        "power_line": "Overhead AC line",
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation(
            source_path=source_path
        ).get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Technology Data for Energy Transport",
            author=["Danish Energy Agency"],
            publication="Danish Energy Agency",
            publication_year=2026,
            url=(
                "https://ens.dk/en/analyses-and-statistics/technology-data-transport-energy"
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
    def get_lifetime(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """
        Get the lifetime of a transport technology.
        """
        if proxy_element_name is not None:
            technology_name = proxy_element_name
            proxy_str = f" (proxy for {technology.name})"
        else:
            technology_name = technology.name
            proxy_str = ""
        if technology_name not in self.LIFETIMES:
            raise ValueError(
                f"The lifetime of technology '{technology_name}' is not "
                f"available in the dataset '{self.name}'."
            )
        attr = technology.lifetime
        return attr.set_data(
            default_value=self.LIFETIMES[technology_name],
            source=SourceInformation(
                description=(
                    f"The lifetime of {technology_name}{proxy_str} is based on "
                    f"{self.SOURCE_SHEET[technology_name]} of the energy transport "
                    "catalogue of the Danish Energy Agency."
                ),
                metadata=self.metadata,
            ),
        )

    def get_construction_time(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """
        Get the construction time of a transport technology.
        """
        if proxy_element_name is not None:
            technology_name = proxy_element_name
            proxy_str = f" (proxy for {technology.name})"
        else:
            technology_name = technology.name
            proxy_str = ""
        if technology_name not in self.CONSTRUCTION_TIMES:
            raise ValueError(
                f"The construction time of technology '{technology_name}' is not "
                f"available in the dataset '{self.name}'."
            )
        attr = technology.construction_time
        return attr.set_data(
            default_value=self.CONSTRUCTION_TIMES[technology_name],
            source=SourceInformation(
                description=(
                    f"The construction time of {technology_name}{proxy_str} is based "
                    f"on {self.SOURCE_SHEET[technology_name]} of the energy transport "
                    "catalogue of the Danish Energy Agency."
                ),
                metadata=self.metadata,
            ),
        )

    def get_transport_loss_factor_linear(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """
        Get the linear transport loss factor of a transport technology.
        """
        if proxy_element_name is not None:
            technology_name = proxy_element_name
            proxy_str = f" (proxy for {technology.name})"
        else:
            technology_name = technology.name
            proxy_str = ""
        if technology_name not in self.TRANSPORT_LOSSES_PER_KM:
            raise ValueError(
                f"The transport losses of technology '{technology_name}' are "
                f"not available in the dataset '{self.name}'."
            )
        transport_losses = self.TRANSPORT_LOSSES_PER_KM[technology_name]
        attr = technology.transport_loss_factor_linear
        return attr.set_data(
            default_value=transport_losses,
            unit="1/km",
            source=SourceInformation(
                description=(
                    f"The transport losses of {technology_name}{proxy_str} are based "
                    f"on the {self.SOURCE_SHEET[technology_name]} of the energy "
                    "transport catalogue of the Danish Energy Agency."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capex_per_distance_transport_onshore(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> float:
        """
        Get the distance-specific capex of a transport technology, in Euro/MW/km.
        """
        return self._get_cost_per_distance(
            self.CAPEX_PER_DISTANCE,
            technology,
            proxy_element_name,
            variable="distance-specific capex",
        )

    def get_opex_fixed_onshore(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> float:
        """
        Get the distance-specific fixed opex of a transport technology, in
        Euro/MW/km.
        """
        return self._get_cost_per_distance(
            self.OPEX_FIXED_PER_DISTANCE,
            technology,
            proxy_element_name,
            variable="distance-specific fixed opex",
        )

    def _get_cost_per_distance(
        self,
        costs: dict[str, float],
        technology: TransportTechnology,
        proxy_element_name: str | None,
        variable: str,
    ) -> float:
        """
        Get a distance-specific cost, corrected for inflation.
        """
        technology_name = proxy_element_name or technology.name
        if technology_name not in costs:
            raise ValueError(
                f"The {variable} of technology '{technology_name}' is not "
                f"available in the dataset '{self.name}'."
            )
        return costs[technology_name] * self.get_inflation_rate(
            base_year=self.MONEY_YEARS[technology_name],
            target_year=technology.settings.time.price_year,
        )
