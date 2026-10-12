from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.datasets.dataset_collections.edges import Edges
from zen_europe.datasets.datasets.technology.ammonia_pipelines_galimova import (
    AmmoniaPipelinesGalimova,
)
from zen_europe.datasets.datasets.technology.dea_carbon_transport import (
    DEACarbonTransport,
)
from zen_europe.datasets.datasets.technology.dea_energy_transport import (
    DEAEnergyTransport,
)
from zen_europe.datasets.datasets.technology.hydrogen_pipelines_miao import (
    HydrogenPipelinesMiao,
)
from zen_europe.datasets.datasets.technology.methanol_pipelines_galimova import (
    MethanolPipelinesGalimova,
)
from zen_europe.utils.constants import Constants

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import Attribute, DatasetCollection, TransportTechnology
from zen_creator.datasets.datasets.metadata import MetadataTree
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings


class TransportTechnologiesCosts(DatasetCollection):
    """Extracting costs for transport technologies.

    The costs are reported per unit of transported power and per km of
    distance. Where the source reports a separate offshore cost, that cost is
    used on the edges that do not connect two adjacent countries, provided
    settings.investment.account_for_offshore_transport is set.
    """

    name = "transport_technologies_costs"

    # dataset that reports the cost of each transport technology
    SOURCES: Dict[str, str] = {
        "power_line": "dea_energy_transport",
        "natural_gas_pipeline": "dea_energy_transport",
        "carbon_pipeline": "dea_carbon_transport",
        "hydrogen_pipeline": "hydrogen_pipelines_miao",
        "ammonia_pipeline": "ammonia_pipelines_galimova",
        "methanol_pipeline": "methanol_pipelines_galimova",
        "olefin_pipeline": "ammonia_pipelines_galimova",
    }
    # An olefin pipeline is sized by the mass flow of its product, while the
    # ammonia pipeline its cost comes from is sized by the transported power,
    # so that cost is rebased with the energy content of ammonia, in MWh per
    # ton. An olefin pipeline is thereby assumed to cost as much as an ammonia
    # pipeline that transports the same mass flow.
    ENERGY_CONTENT_PER_TON = {
        "olefin_pipeline": Constants.AMMONIA_GWH_PER_TON * 1000,
    }
    # the DEA energy transport catalogue reports no offshore cost for
    # natural gas pipelines, so the offshore cost increase of the ammonia
    # pipelines of Galimova et al. (2023) is used as a proxy. Replace it once
    # an offshore cost of natural gas pipelines is available.
    OFFSHORE_COST_INCREASE_PROXY = {
        "natural_gas_pipeline": "ammonia_pipelines_galimova",
    }

    def __init__(
        self, settings: Settings, source_path: Path | str, set_nodes: list[str]
    ):
        self.settings = settings
        self.set_nodes = set_nodes
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "dea_energy_transport": DEAEnergyTransport(source_path=self.source_path),
            "dea_carbon_transport": DEACarbonTransport(source_path=self.source_path),
            "ammonia_pipelines_galimova": AmmoniaPipelinesGalimova(
                source_path=self.source_path
            ),
            "hydrogen_pipelines_miao": HydrogenPipelinesMiao(
                source_path=self.source_path
            ),
            "methanol_pipelines_galimova": MethanolPipelinesGalimova(
                source_path=self.source_path
            ),
        }

    # -------- outward-facing accessors ------------------
    def get_capex_per_distance_transport(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """Get the distance-specific capex of a transport technology."""
        return self._set_cost_per_distance(
            technology,
            technology.capex_per_distance_transport,
            onshore_method="get_capex_per_distance_transport_onshore",
            offshore_method="get_capex_per_distance_transport_offshore",
            description="distance-specific investment cost",
            proxy_element_name=proxy_element_name,
        )

    def get_opex_specific_fixed_per_distance(
        self, technology: TransportTechnology, proxy_element_name: str | None = None
    ) -> Attribute:
        """Get the distance-specific fixed opex of a transport technology.

        The cost is set on opex_specific_fixed, which ZEN-garden reads per unit
        of capacity rather than per unit of capacity and distance.
        TODO implement opex_specific_fixed_per_distance in ZEN-garden
        """
        return self._set_cost_per_distance(
            technology,
            technology.opex_specific_fixed,
            onshore_method="get_opex_fixed_onshore",
            offshore_method="get_opex_fixed_offshore",
            description="distance-specific fixed operational cost",
            proxy_element_name=proxy_element_name,
        )

    # -------- cost internals ------------------
    def _set_cost_per_distance(
        self,
        technology: TransportTechnology,
        attr: Attribute,
        onshore_method: str,
        offshore_method: str,
        description: str,
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Set a distance-specific cost attribute of a transport technology.

        The onshore cost is the default value of the attribute, while the
        offshore cost is only set for the offshore edges.
        """
        dataset = self._get_source(technology)
        multiplier, unit = self._get_rebasing(technology)
        onshore_cost = multiplier * self._get_cost(
            dataset, onshore_method, technology, proxy_element_name
        )

        notes = []
        metadata: Dict[str, MetadataTree] = {dataset.name: dataset.metadata}
        if proxy_element_name is not None:
            notes.append(f"The cost of {proxy_element_name} is used as a proxy.")
        if multiplier != 1.0:
            notes.append(
                f"The cost is rebased from the transported power onto the "
                f"transported mass with an energy content of {multiplier:.4g} "
                f"MWh per ton."
            )

        offshore_cost, offshore_dataset = self._get_offshore_cost(
            technology,
            dataset,
            offshore_method,
            proxy_element_name,
            onshore_cost,
            multiplier,
        )
        offshore_df = None
        if offshore_cost is not None:
            offshore_edges = self._get_offshore_edges(technology)
            if not offshore_edges.empty:
                offshore_df = pd.Series(
                    data=offshore_cost,
                    index=offshore_edges,
                    name=attr.name,
                    dtype=float,
                )
                notes.append(
                    f"On the {len(offshore_edges)} edges that do not connect "
                    f"two adjacent countries, the offshore cost of "
                    f"{offshore_cost:.4g} {unit} applies."
                )
                if offshore_dataset is not None and offshore_dataset is not dataset:
                    metadata[offshore_dataset.name] = offshore_dataset.metadata
                    notes.append(
                        f"The offshore cost increase of "
                        f"{offshore_dataset.name} is used as a proxy, as the "
                        f"onshore cost source reports no offshore cost."
                    )

        source = SourceInformation(
            description=" ".join(
                [
                    f"The {description} of {technology.name} is based on "
                    f"{cast(Any, dataset.metadata).title}."
                ]
                + notes
            ),
            metadata=metadata if len(metadata) > 1 else dataset.metadata,
        )
        return attr.set_data(
            default_value=onshore_cost,
            df=offshore_df,
            unit=unit,
            source=source,
        )

    def _get_source(self, technology: TransportTechnology) -> Dataset[Any]:
        """Get the dataset that reports the cost of a transport technology."""
        if technology.name not in self.SOURCES:
            raise ValueError(
                f"No cost source is available for technology "
                f"'{technology.name}' in the dataset collection '{self.name}'."
            )
        return cast("Dataset[Any]", self.data[self.SOURCES[technology.name]])

    def _get_rebasing(self, technology: TransportTechnology) -> tuple[float, str]:
        """Get the multiplier and the unit of the cost of a technology.

        The cost is expressed per unit of the capacity the technology is sized
        by, so its unit follows the power unit of the technology.
        """
        multiplier = self.ENERGY_CONTENT_PER_TON.get(technology.name, 1.0)
        return multiplier, f"Euro/({technology.power_unit})/km"

    def _get_offshore_cost(
        self,
        technology: TransportTechnology,
        dataset: Dataset[Any],
        offshore_method: str,
        proxy_element_name: str | None,
        onshore_cost: float,
        multiplier: float,
    ) -> tuple[float | None, Dataset[Any] | None]:
        """Get the offshore cost of a transport technology, and its source.

        Returns no cost if offshore transport is not accounted for, or if
        neither the source of the technology nor a proxy source reports an
        offshore cost.
        """
        if not self.settings.investment.account_for_offshore_transport:
            return None, None
        if hasattr(dataset, offshore_method):
            return (
                multiplier
                * self._get_cost(
                    dataset, offshore_method, technology, proxy_element_name
                ),
                dataset,
            )
        proxy_dataset_name = self.OFFSHORE_COST_INCREASE_PROXY.get(technology.name)
        if proxy_dataset_name is None:
            return None, None
        proxy_dataset = cast("Dataset[Any]", self.data[proxy_dataset_name])
        cost_increase = cast(Any, proxy_dataset).get_offshore_cost_increase()
        return onshore_cost * cost_increase, proxy_dataset

    def _get_offshore_edges(self, technology: TransportTechnology) -> pd.Index:
        """Get the edges of the model that cross the sea."""
        edges = Edges(source_path=self.source_path)
        return edges.get_edges_offshore(technology, self.set_nodes)

    @staticmethod
    def _get_cost(
        dataset: Dataset[Any],
        method: str,
        technology: TransportTechnology,
        proxy_element_name: str | None,
    ) -> float:
        """Get a cost of a transport technology from one of the datasets."""
        getter = getattr(cast(Any, dataset), method)
        if proxy_element_name is None:
            return float(getter(technology))
        return float(getter(technology, proxy_element_name))
