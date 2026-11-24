from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Technology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.technology.enspreso1 import ENSPRESO1
from zen_europe.datasets.datasets.technology.enspreso2 import ENSPRESO2
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
            "enspreso1": ENSPRESO1(self.source_path),
            "enspreso2": ENSPRESO2(self.source_path),
            "euro_calliope": EuroCalliope(self.source_path),
        }

    def get_capacity_limit(self, element: Technology) -> Attribute:
        """
        Get the potential capacity for renewable technologies.

        Wind uses ENSPRESO 2, with ENSPRESO 1 (medium) for the UK onshore, which
        ENSPRESO 2 does not cover. Photovoltaics uses ENSPRESO 1, with EuroCalliope
        as a fallback for the nodes ENSPRESO 1 does not cover (CH, NO).
        """
        if element.name == "wind_offshore":
            enspreso2 = cast(ENSPRESO2, self.data["enspreso2"])
            data = enspreso2.get_capacity_limit(element)
            description = (
                "Potential capacity of offshore wind is the fixed-bottom potential "
                "of the ENSPRESO 2 reference scenario (sites with a capacity factor "
                "of at least 30%)."
            )
        elif element.name == "wind_onshore":
            enspreso2 = cast(ENSPRESO2, self.data["enspreso2"])
            enspreso1 = cast(ENSPRESO1, self.data["enspreso1"])
            data = enspreso2.get_capacity_limit(element)
            missing_nodes = pd.Index(element.model.config.system.set_nodes).difference(
                data.index
            )
            fallback = enspreso1.get_capacity_limit(element)
            data = pd.concat([data, fallback.reindex(missing_nodes)])
            description = (
                "Potential capacity of onshore wind is the ENSPRESO 2 high scenario "
                "(500 m setback from settlements, sites with a capacity factor of at "
                "least 20%). ENSPRESO 2 does not cover the UK, for which the medium "
                "scenario of ENSPRESO 1 is used."
            )
        else:
            enspreso_dataset = cast(ENSPRESO1, self.data["enspreso1"])
            euro_calliope_dataset = cast(EuroCalliope, self.data["euro_calliope"])
            data = enspreso_dataset.get_capacity_limit(element)
            missing_nodes = pd.Index(element.model.config.system.set_nodes).difference(
                data.index
            )
            for node in missing_nodes:
                data.loc[node] = euro_calliope_dataset.get_capacity_limit(element, node)
            description = (
                "Potential capacity data for renewable technologies is derived "
                "from the high scenario of the ENSPRESO 1 dataset. For missing "
                "nodes (CH, NO), the EuroCalliope dataset is used as a fallback."
            )
        data = data.sort_index()
        data.index.name = "node"
        data.name = "capacity_limit"
        source = SourceInformation(description=description, metadata=self.metadata)
        return element.capacity_limit.set_data(
            source=source,
            df=data,
            default_value=0.0,
            unit="GW",
        )
