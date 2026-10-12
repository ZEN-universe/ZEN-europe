from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, SourceInformation, StorageTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class BatteryStorageNREL(Dataset[pd.DataFrame]):
    """
    Utility-scale battery storage dataset class from the NREL Annual
    Technology Baseline (2023).

    Provides the reference storage duration of utility-scale batteries, which
    fixes the ratio between the energy and the power capacity.
    """

    name = "battery_storage_nrel"

    ENERGY_TO_POWER_RATIOS = {
        "battery": 4,
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="2023 Annual Technology Baseline: Utility-Scale Battery Storage",
            author=["National Renewable Energy Laboratory"],
            publication="National Renewable Energy Laboratory",
            publication_year=2023,
            url="https://atb.nrel.gov/electricity/2023/utility-scale_battery_storage",
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
    def get_energy_to_power_ratio_min(self, technology: StorageTechnology) -> Attribute:
        """
        Get the minimum energy-to-power ratio of a storage technology.
        """
        return self._set_energy_to_power_ratio(
            technology, technology.energy_to_power_ratio_min
        )

    def get_energy_to_power_ratio_max(self, technology: StorageTechnology) -> Attribute:
        """
        Get the maximum energy-to-power ratio of a storage technology.
        """
        return self._set_energy_to_power_ratio(
            technology, technology.energy_to_power_ratio_max
        )

    def _set_energy_to_power_ratio(
        self, technology: StorageTechnology, attr: Attribute
    ) -> Attribute:
        """
        Set an energy-to-power ratio attribute to the storage duration.
        """
        energy_to_power_ratio = self._get_e2p_ratio(technology)
        return attr.set_data(
            default_value=energy_to_power_ratio,
            unit="h",
            source=SourceInformation(
                description=(
                    f"The energy-to-power ratio of {technology.name} is fixed "
                    f"to {energy_to_power_ratio} hours, the reference storage "
                    "duration of utility-scale battery storage in the NREL "
                    "Annual Technology Baseline."
                ),
                metadata=self.metadata,
            ),
        )

    def _get_e2p_ratio(self, technology: StorageTechnology) -> float:
        """
        Get the energy-to-power ratio of a storage technology.
        """
        if technology.name not in self.ENERGY_TO_POWER_RATIOS:
            raise ValueError(
                f"The energy-to-power ratio of technology '{technology.name}' "
                f"is not available in the dataset '{self.name}'."
            )
        return self.ENERGY_TO_POWER_RATIOS[technology.name]
