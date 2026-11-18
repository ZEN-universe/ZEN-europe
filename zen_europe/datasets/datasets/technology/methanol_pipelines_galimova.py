from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.financial.ECB import ECBInflation

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import (
    Attribute,
    SourceInformation,
    TransportTechnology,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class MethanolPipelinesGalimova(Dataset[dict[str, pd.DataFrame]]):
    """
    Methanol pipelines dataset class from Galimova et al. (2025).

    This class implements the specific behavior for the Methanol Pipelines dataset.
    """

    name = "methanol_pipelines_galimova"

    MONEY_YEAR = 2019

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation(
            source_path=source_path
        ).get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Analysis of green e-methanol supply costs: Domestic production in "
                "Europe versus imports via pipelines and sea shipping"
            ),
            author=[
                "Tansu Galimova",
                "Mahdi Fasihi",
                "Dmitrii Bogdanov",
                "Gabriel Lopez",
                "Christian Breyer",
            ],
            publication="Renewable Energy",
            publication_year=2025,
            url="https://www.sciencedirect.com/science/article/pii/S0960148124024042",
            doi="https://doi.org/10.1016/j.renene.2024.122336",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        # TODO there is no data to be implemented
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    @staticmethod
    def get_offshore_cost_increase() -> float:
        """
        Get the offshore cost increase factor for offshore pipelines.

        Returns:
            float: Offshore cost increase factor.
        """
        return 1.4

    def get_capex_per_distance_transport_onshore(
        self, technology: TransportTechnology
    ) -> float:
        """
        Get the distance-specific capex of a transport technology.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the capex.
        """
        assert technology.name == "methanol_pipeline", (
            f"The distance-specific capex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return (
            0.098
            * self.get_inflation_rate(
                base_year=self.MONEY_YEAR,
                target_year=technology.settings.time.price_year,
            )
            * 1000
        )  # Euro/km/MW

    def get_capex_per_distance_transport_offshore(
        self, technology: TransportTechnology
    ) -> float:
        """
        Get the distance-specific capex of a transport technology.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the capex.
        """
        assert technology.name == "methanol_pipeline", (
            f"The distance-specific capex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return (
            self.get_offshore_cost_increase()
            * self.get_capex_per_distance_transport_onshore(technology)
        )

    def get_opex_fixed_onshore(self, technology: TransportTechnology) -> float:
        """
        Get the fixed opex of a methanol pipeline for onshore transmission.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the opex.
        """
        assert technology.name == "methanol_pipeline", (
            f"The fixed opex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return (
            self.get_capex_per_distance_transport_onshore(technology) * 0.03
        )  # 3% of capex per year

    def get_opex_fixed_offshore(self, technology: TransportTechnology) -> float:
        """
        Get the fixed opex of a methanol pipeline for offshore transmission.

        Args:
            technology (TransportTechnology): The transport technology for which to get
                the opex.
        """
        assert technology.name == "methanol_pipeline", (
            f"The fixed opex of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        return (
            self.get_capex_per_distance_transport_offshore(technology) * 0.03
        )  # 3% of capex per year

    def get_lifetime(self, technology: TransportTechnology) -> Attribute:
        """
        Get the lifetime of a transport technology.
        """
        assert technology.name == "methanol_pipeline", (
            f"The lifetime of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        attr = technology.lifetime
        return attr.set_data(
            default_value=40,
            source=SourceInformation(
                description=(
                    f"The lifetime of {technology.name} is based on "
                    f"Galimova et al. (2025) of the methanol pipelines dataset."
                ),
                metadata=self.metadata,
            ),
        )

    def get_transport_loss_factor_linear(
        self, technology: TransportTechnology
    ) -> Attribute:
        """
        Get the losses of a transport technology.
        """
        assert technology.name == "methanol_pipeline", (
            f"The losses of technology '{technology.name}' is not "
            f"available in the dataset '{self.name}'."
        )
        attr = technology.transport_loss_factor_linear
        return attr.set_data(
            default_value=0,  # 0% per 1000 km
            unit="1/km",
            source=SourceInformation(
                description=(
                    f"The losses of {technology.name} is based on "
                    f"Galimova et al. (2025) of the methanol pipelines dataset."
                ),
                metadata=self.metadata,
            ),
        )
