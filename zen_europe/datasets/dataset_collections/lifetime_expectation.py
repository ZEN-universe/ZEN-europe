from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Element


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings


class LifetimeExpectation(DatasetCollection):
    """Extracting lifetime expectation data for various technologies.

    Either we get the median lifetime of all decommissioned plants of a technology
    or we use the default lifetime from the technology database.
    """

    name = "lifetime_expectation"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "tech_db": TechnologyCostDatabase(self.settings, self.source_path),
            "powerplantmatching": PowerPlantMatching(self.source_path),
        }

    def get_lifetime(self, element: Element) -> Attribute:
        """
        Get the lifetime for a given technology.

        Either we get the median lifetime of all decommissioned plants of a technology
            or we use the default lifetime from the technology database.

        We first check if the lifetime can be estimated from the PowerPlantMatching
        dataset.
        If less than 25% of the plants are decommissioned, we fall back to the
        technology database.
        """
        powerplantmatching = self.data["powerplantmatching"]
        tech_db = self.data["tech_db"]
        lifetime = powerplantmatching.estimate_lifetime(element, threshold=0.25)
        def_attr = tech_db.get_lifetime(element)
        if lifetime is None or lifetime < def_attr.default_value:
            return def_attr
        else:
            attr = element.lifetime
            attr.set_data(
                default_value=lifetime,
                source=SourceInformation(
                    description=(
                        "The lifetime is estimated based on the decommissioned plants "
                        "from the PowerPlantMatching dataset. If less than 25% of the "
                        "plants are decommissioned, or if the estimated lifetime is "
                        "lower than the default lifetime from the technology database, "
                        "the default lifetime from the technology database is used."
                    ),
                    metadata=powerplantmatching.metadata,
                ),
            )
            return attr
