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


class AmmoniaPipelinesGalimova(Dataset[dict[str, pd.DataFrame]]):
    """
    Ammonia pipelines dataset class from Galimova et al. (2023).

    This class implements the specific behavior for the Ammonia Pipelines dataset.
    """

    name = "ammonia_pipelines_galimova"

    MONEY_YEAR = 2019
    TECHNOLOGY = "ammonia_pipeline"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation(
            source_path=source_path
        ).get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Feasibility of green ammonia trading via pipelines and shipping: "
                "Cases of Europe, North Africa, and South America"
            ),
            author=[
                "Tansu Galimova",
                "Mahdi Fasihi",
                "Dmitrii Bogdanov",
                "Christian Breyer",
            ],
            publication="Journal of Cleaner Production",
            publication_year=2023,
            url="https://www.sciencedirect.com/science/article/pii/S095965262303370X",
            doi="https://doi.org/10.1016/j.jclepro.2023.139212",
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

    def _check_technology(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> str:
        """
        Check that the dataset covers the technology and return the proxy note.

        Args:
            technology (TransportTechnology): The transport technology.
            proxy_element_name (str | None): The technology whose data is used
                as a proxy for the technology.
        """
        technology_name = proxy_element_name or technology.name
        if technology_name != self.TECHNOLOGY:
            raise ValueError(
                f"The data of technology '{technology_name}' is not available "
                f"in the dataset '{self.name}'."
            )
        if proxy_element_name is None:
            return ""
        return f" (proxy for {technology.name})"

    def get_capex_per_distance_transport_onshore(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> float:
        """
        Get the distance-specific capex of a transport technology.

        Args:
            technology (TransportTechnology): The transport technology.
            proxy_element_name (str | None): The technology used as a proxy.
        """
        self._check_technology(technology, proxy_element_name)
        return (
            0.617
            * self.get_inflation_rate(
                base_year=self.MONEY_YEAR,
                target_year=technology.settings.time.price_year,
            )
            * 1000
        )  # Euro/km/MW

    def get_capex_per_distance_transport_offshore(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> float:
        """
        Get the distance-specific capex of a transport technology.

        Args:
            technology (TransportTechnology): The transport technology.
            proxy_element_name (str | None): The technology used as a proxy.
        """
        self._check_technology(technology, proxy_element_name)
        return (
            self.get_offshore_cost_increase()
            * self.get_capex_per_distance_transport_onshore(
                technology, proxy_element_name
            )
        )

    def get_opex_fixed_onshore(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> float:
        """
        Get the fixed opex of an ammonia pipeline for onshore transmission.

        Args:
            technology (TransportTechnology): The transport technology.
            proxy_element_name (str | None): The technology used as a proxy.
        """
        self._check_technology(technology, proxy_element_name)
        return (
            self.get_capex_per_distance_transport_onshore(
                technology, proxy_element_name
            )
            * 0.03
        )  # 3% of capex per year

    def get_opex_fixed_offshore(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> float:
        """
        Get the fixed opex of an ammonia pipeline for offshore transmission.

        Args:
            technology (TransportTechnology): The transport technology.
            proxy_element_name (str | None): The technology used as a proxy.
        """
        self._check_technology(technology, proxy_element_name)
        return (
            self.get_capex_per_distance_transport_offshore(
                technology, proxy_element_name
            )
            * 0.03
        )  # 3% of capex per year

    def get_lifetime(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """
        Get the lifetime of a transport technology.
        """
        proxy_str = self._check_technology(technology, proxy_element_name)
        attr = technology.lifetime
        return attr.set_data(
            default_value=40,
            source=SourceInformation(
                description=(
                    f"The lifetime of {self.TECHNOLOGY}{proxy_str} is based on "
                    f"Galimova et al. (2023) of the ammonia pipelines dataset."
                ),
                metadata=self.metadata,
            ),
        )

    def get_transport_loss_factor_linear(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """
        Get the losses of a transport technology.
        """
        proxy_str = self._check_technology(technology, proxy_element_name)
        attr = technology.transport_loss_factor_linear
        return attr.set_data(
            default_value=0.1 / 100 / 1000,  # 0.1% per 1000 km
            unit="1/km",
            source=SourceInformation(
                description=(
                    f"The losses of {self.TECHNOLOGY}{proxy_str} are based on "
                    f"Galimova et al. (2023) of the ammonia pipelines dataset."
                ),
                metadata=self.metadata,
            ),
        )
