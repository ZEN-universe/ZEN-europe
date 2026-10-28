from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, SourceInformation, TransportTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBInflation


class DEACarbonTransport(Dataset[dict[str, pd.DataFrame]]):
    """
    CO2 transport dataset class from the technology catalogue for carbon
    capture, transport and storage of the Danish Energy Agency.

    Provides the lifetime of CO2 pipelines, read from the CO2 transport data
    sheets of the catalogue.
    """

    name = "dea_carbon_transport"

    MONEY_YEAR = 2020
    LIFETIMES = {
        "carbon_pipeline": 50,
    }

    CONSTRUCTION_TIMES = {
        "carbon_pipeline": 1,
    }

    # 120 tCO2/h
    CAPEX_ONSHORE = {
        "carbon_pipeline": 13 * 1000,  # Euro/(tCO2/h)/km -> Euro/(tCO2/h)/km
    }
    CAPEX_OFFSHORE = {
        "carbon_pipeline": 33 * 1000,  # Euro/(tCO2/h)/km -> Euro/(tCO2/h)/km
    }
    OPEX_FIXED = {
        "carbon_pipeline": 20,  # Euro/(tCO2/h)/km/year
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation(
            source_path=source_path
        ).get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Technology Data for Carbon Capture, Transport and Storage",
            author=["Danish Energy Agency"],
            publication="Danish Energy Agency",
            publication_year=2026,
            url=(
                "https://ens.dk/en/analyses-and-statistics/"
                "technology-data-carbon-capture-transport-and-storage"
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
    def get_lifetime(self, technology: TransportTechnology) -> Attribute:
        """
        Get the lifetime of a transport technology.
        """
        if technology.name not in self.LIFETIMES:
            raise ValueError(
                f"The lifetime of technology '{technology.name}' is not "
                f"available in the dataset '{self.name}'."
            )
        attr = technology.lifetime
        return attr.set_data(
            default_value=self.LIFETIMES[technology.name],
            source=SourceInformation(
                description=(
                    f"The lifetime of {technology.name} is based on the CO2 "
                    "transport data of the carbon capture, transport and "
                    "storage catalogue of the Danish Energy Agency."
                ),
                metadata=self.metadata,
            ),
        )

    def get_construction_time(self, technology: TransportTechnology) -> Attribute:
        """
        Get the construction time of a transport technology.
        """
        if technology.name not in self.CONSTRUCTION_TIMES:
            raise ValueError(
                f"The construction time of technology '{technology.name}' is "
                f"not available in the dataset '{self.name}'."
            )
        attr = technology.construction_time
        return attr.set_data(
            default_value=self.CONSTRUCTION_TIMES[technology.name],
            source=SourceInformation(
                description=(
                    f"The construction time of {technology.name} is based on "
                    "the CO2 transport data of the carbon capture, transport "
                    "and storage catalogue of the Danish Energy Agency."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capex_per_distance_transport_onshore(
        self, technology: TransportTechnology
    ) -> float:
        """
        Get the distance-specific capex of an onshore CO2 pipeline.
        """
        return self._get_cost_per_distance(
            self.CAPEX_ONSHORE, technology, variable="distance-specific capex"
        )

    def get_capex_per_distance_transport_offshore(
        self, technology: TransportTechnology
    ) -> float:
        """
        Get the distance-specific capex of an offshore CO2 pipeline.
        """
        return self._get_cost_per_distance(
            self.CAPEX_OFFSHORE, technology, variable="distance-specific capex"
        )

    def get_opex_fixed_onshore(self, technology: TransportTechnology) -> float:
        """
        Get the distance-specific fixed opex of an onshore CO2 pipeline.
        """
        return self._get_cost_per_distance(
            self.OPEX_FIXED, technology, variable="distance-specific fixed opex"
        )

    def get_opex_fixed_offshore(self, technology: TransportTechnology) -> float:
        """
        Get the distance-specific fixed opex of an offshore CO2 pipeline.

        The catalogue reports the same fixed opex for both, as it scales with
        the transported amount rather than with the type of the pipeline.
        """
        return self.get_opex_fixed_onshore(technology)

    def _get_cost_per_distance(
        self, costs: Mapping[str, float], technology: TransportTechnology, variable: str
    ) -> float:
        """
        Get a distance-specific cost, corrected for inflation.
        """
        if technology.name not in costs:
            raise ValueError(
                f"The {variable} of technology '{technology.name}' is not "
                f"available in the dataset '{self.name}'."
            )
        return costs[technology.name] * self.get_inflation_rate(
            base_year=self.MONEY_YEAR,
            target_year=technology.settings.time.price_year,
        )
