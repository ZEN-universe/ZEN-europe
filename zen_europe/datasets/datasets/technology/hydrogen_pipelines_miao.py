from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import (
    TransportTechnology,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class HydrogenPipelinesMiao(Dataset[dict[str, pd.DataFrame]]):
    """
    Hydrogen pipelines dataset class from Miao et al. (2021).

    This class implements the specific behavior for the Hydrogen Pipelines dataset.
    """

    name = "hydrogen_pipelines_miao"

    MONEY_YEAR = 2017
    TRANSMISSION_CAPACITY = 1000  # MW

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation(
            source_path=source_path
        ).get_inflation_rate
        self.get_dollar2euro = ECBDollar2Euro(source_path=source_path).get_dollar2euro

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Long-distance renewable hydrogen transmission via cables and pipelines"
            ),
            author=["Bin Miao", "Lorenzo Giordano", "Siew Hwa Chan"],
            publication="International Journal of Hydrogen Energy",
            publication_year=2021,
            url="https://www.sciencedirect.com/science/article/pii/S0360319921009137",
            doi="https://doi.org/10.1016/j.ijhydene.2021.03.067",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        # TODO there is no data to be implemented
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    def _correct_for_capacity_dollar_year(
        self, capex_per_distance: float, price_year: int
    ) -> float:
        """
        Correct the capex_per_distance for the dollar year of the capacity.

        Args:
            capex_per_distance (float): The capex_per_distance to be corrected.
            price_year (int): Year to which the monetary value is rebased.
        """
        capex_per_distance = capex_per_distance * self.get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=price_year
        )
        capex_per_distance = capex_per_distance * self.get_dollar2euro(
            year=self.MONEY_YEAR
        )
        capex_per_distance = capex_per_distance / self.TRANSMISSION_CAPACITY

        return capex_per_distance * 1e6  # Euro/MW/km

    def get_capex_per_distance_transport_onshore(
        self, technology: TransportTechnology
    ) -> float:
        """
        Get the distance-specific capex of a hydrogen pipeline for onshore transmission.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the capex.
        """
        assert technology.name == "hydrogen_pipeline", (
            f"The distance-specific capex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return self._correct_for_capacity_dollar_year(
            capex_per_distance=0.34,  # million USD/km for a 1000
            price_year=technology.settings.time.price_year,
        )

    def get_capex_per_distance_transport_offshore(
        self, technology: TransportTechnology
    ) -> float:
        """
        Get the distance-specific capex of a hydrogen pipeline for offshore
        transmission.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the capex.
        """
        assert technology.name == "hydrogen_pipeline", (
            f"The distance-specific capex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return self._correct_for_capacity_dollar_year(
            capex_per_distance=0.96,  # million USD/km for a 1000
            price_year=technology.settings.time.price_year,
        )

    def get_opex_fixed_onshore(self, technology: TransportTechnology) -> float:
        """
        Get the fixed opex of a hydrogen pipeline for onshore transmission.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the opex.
        """
        assert technology.name == "hydrogen_pipeline", (
            f"The fixed opex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return (
            self.get_capex_per_distance_transport_onshore(technology) * 0.04
        )  # 4% of capex per year

    def get_opex_fixed_offshore(self, technology: TransportTechnology) -> float:
        """
        Get the fixed opex of a hydrogen pipeline for offshore transmission.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the opex.
        """
        assert technology.name == "hydrogen_pipeline", (
            f"The fixed opex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return (
            self.get_capex_per_distance_transport_offshore(technology) * 0.07
        )  # 7% of capex per year
