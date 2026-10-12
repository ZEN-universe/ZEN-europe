from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Technology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.technology.enspreso_v1 import ENSPRESOV1
from zen_europe.datasets.datasets.technology.euro_calliope import EuroCalliope


class PotentialCapacityRenewables(DatasetCollection):
    """Extracting potential capacity data for renewable technologies."""

    name = "potential_capacity_renewables"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "enspreso_v1": ENSPRESOV1(self.source_path),
            "euro_calliope": EuroCalliope(self.source_path),
        }

    def get_capacity_limit(self, element: Technology) -> Attribute:
        """
        Get the potential capacity for renewable technologies.

        This function retrieves the potential capacity data for the specified element.
        """
        enspreso_dataset = cast(ENSPRESOV1, self.data["enspreso_v1"])
        euro_calliope_dataset = cast(EuroCalliope, self.data["euro_calliope"])
        data = enspreso_dataset.get_capacity_limit(element)
        if not element.name == "wind_offshore":
            missing_nodes = pd.Index(element.model.config.system.set_nodes).difference(
                data.index
            )
            for node in missing_nodes:
                data.loc[node] = euro_calliope_dataset.get_capacity_limit(element, node)
        data = data.sort_index()
        data.index.name = "node"
        data.name = "capacity_limit"
        source = SourceInformation(
            description=(
                "Potential capacity data for renewable technologies is derived "
                "from the ENSPRESO v1 dataset."
                " For missing nodes (CH, NO), the EuroCalliope dataset is used "
                " for photovolatics and onshore wind as a fallback."
            ),
            metadata=self.metadata,
        )
        return element.capacity_limit.set_data(
            source=source,
            df=data,
            default_value=0.0,
            unit="GW",
        )
