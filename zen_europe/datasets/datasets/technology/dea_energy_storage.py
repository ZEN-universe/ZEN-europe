from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, SourceInformation, StorageTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class DEAEnergyStorage(Dataset[pd.DataFrame]):
    """
    Energy storage dataset class from the technology catalogue for energy
    storage of the Danish Energy Agency.

    Provides the lifetime and the round-trip efficiency of hydrogen storage
    caverns, read from the data sheets of the catalogue. The round-trip
    efficiency is split evenly between charging and discharging.
    """

    name = "dea_energy_storage"

    LIFETIMES = {
        "salt_cavern_storage": 100,
    }
    EFFICIENCIES_ROUND_TRIP = {
        "salt_cavern_storage": 0.99,
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Technology Data for Energy Storage",
            author=["Danish Energy Agency"],
            publication="Danish Energy Agency",
            publication_year=2026,
            url=(
                "https://ens.dk/en/analyses-and-statistics/technology-data-energy-storage"
            ),
            note="Hydrogen storage caverns, assuming pre-existing salt caverns.",
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
    def get_lifetime(self, technology: StorageTechnology) -> Attribute:
        """
        Get the lifetime of a storage technology.
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
                    f"The lifetime of {technology.name} is based on the "
                    "hydrogen storage caverns of the energy storage catalogue "
                    "of the Danish Energy Agency. The caverns are assumed to "
                    "exist already, so they do not retire within the modeling "
                    "horizon."
                ),
                metadata=self.metadata,
            ),
        )

    def get_efficiency_charge(self, technology: StorageTechnology) -> Attribute:
        """
        Get the charging efficiency of a storage technology.
        """
        return self._set_efficiency(technology, technology.efficiency_charge)

    def get_efficiency_discharge(self, technology: StorageTechnology) -> Attribute:
        """
        Get the discharging efficiency of a storage technology.
        """
        return self._set_efficiency(technology, technology.efficiency_discharge)

    def _set_efficiency(
        self, technology: StorageTechnology, attr: Attribute
    ) -> Attribute:
        """
        Set an efficiency attribute to half of the round-trip efficiency.
        """
        if technology.name not in self.EFFICIENCIES_ROUND_TRIP:
            raise ValueError(
                f"The round-trip efficiency of technology '{technology.name}' "
                f"is not available in the dataset '{self.name}'."
            )
        efficiency_round_trip = self.EFFICIENCIES_ROUND_TRIP[technology.name]
        return attr.set_data(
            default_value=np.sqrt(efficiency_round_trip),
            unit="1",
            source=SourceInformation(
                description=(
                    f"The round-trip efficiency of {technology.name} is "
                    f"{efficiency_round_trip} in the energy storage catalogue "
                    "of the Danish Energy Agency and is split evenly between "
                    "charging and discharging."
                ),
                metadata=self.metadata,
            ),
        )
