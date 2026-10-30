from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

from zen_europe.utils.utils import (
    account_for_decommissioned_capacity,
    format_capacity_existing,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import Attribute, ConversionTechnology, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.technology.hydrogen_market_landscape import (
    HydrogenMarketLandscape,
)
from zen_europe.datasets.datasets.technology.rollout_hydrogen_ganter import (
    HydrogenRolloutGanter,
)


class SMRCapacity(DatasetCollection):
    """Extracting the existing capacity of SMR technologies."""

    name = "smr_capacity"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "hydrogen_market_landscape": (HydrogenMarketLandscape(self.source_path)),
            "hydrogen_rollout_ganter": HydrogenRolloutGanter(self.source_path),
        }

    def get_capacity_existing(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the existing capacity of SMR technologies.

        The data is obtained from the near-term infrastructure rollout and
        investment strategies for
        net-zero hydrogen supply chains, based on the work of Alissa Ganter et al.
        (2024). The existing capacity is adjusted for a utilization rate of 0.7,
        which is obtained from the European hydrogen market landscape 2025 report.

        Args:
            technology: The technology for which to get the existing capacity.
        """
        assert (
            technology.name == "SMR"
        ), "This method is only applicable to SMR technologies."
        ganter_dataset = cast(
            HydrogenRolloutGanter, self.data["hydrogen_rollout_ganter"]
        )
        raw_capacity = ganter_dataset.get_capacity_existing_SMR()
        hmlo_dataset = cast(
            HydrogenMarketLandscape, self.data["hydrogen_market_landscape"]
        )
        utilization_rate = hmlo_dataset.get_utilization_rate_SMR()
        raw_capacity /= utilization_rate
        capacity_frame = raw_capacity.to_frame(
            name=technology.settings.time.reference_year - 1
        )
        capacity_frame = account_for_decommissioned_capacity(capacity_frame, technology)
        capacity_frame.index.name = "node"
        capacity_existing = format_capacity_existing(capacity_frame)
        attr = technology.capacity_existing
        source = SourceInformation(
            description=(
                "The existing capacity of SMR is based on data from Ganter et al. "
                "(2024). It is assumed that all current ammonia and refinery "
                "plants are using SMR technology for hydrogen production."
                " A utilization rate of 0.7 is taken from the European "
                "hydrogen market landscape 2025 report."
            ),
            metadata=self.metadata,
        )
        return attr.set_data(df=capacity_existing, source=source, unit="GW")
