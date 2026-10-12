from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, SourceInformation, StorageTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class SelfDischargeAlt(Dataset[pd.DataFrame]):
    """
    Self discharge rates of batteries from Alt et al. (2026).
    """

    name = "self_discharge_alt"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Quantifying the self-discharge of solid-state batteries"),
            author=[
                "Christoph Alt",
                "Jürgen Janek",
            ],
            publication="Nature Energy",
            publication_year=2026,
            url="https://www.nature.com/articles/s41560-026-02038-1",
            doi="https://doi.org/10.1038/s41560-026-02038-1",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        """Set the data for the dataset."""
        return pd.DataFrame()

    def get_self_discharge(self, element: StorageTechnology) -> Attribute:
        """
        Get the self discharge rate for a given storage technology.

        Args:
            element (StorageTechnology):
                The storage technology for which to get the self discharge rate.
        """
        assert (
            element.name == "battery"
        ), "Self discharge rate is only available for batteries."
        attr = element.self_discharge
        # batteries in automotive applications must have SDR < 2%
        monthly_SDR = 2 / 100
        hourly_SDR = 1 - (1 - monthly_SDR) ** (1 / (30 * 24))
        attr.set_data(
            default_value=hourly_SDR,
            unit="1",
            source=SourceInformation(
                description=(
                    "The self-discharge rate of batteries is set to 2% per month "
                    "for automotive applications, which corresponds to an hourly "
                    "self-discharge rate of {:.4g}.".format(hourly_SDR)
                ),
                metadata=self.metadata,
            ),
        )
        return attr
