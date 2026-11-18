from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_europe.elements.storage_technologies.industry_TES import IndustryTES


class Brown2018(Dataset[pd.DataFrame]):
    """Standing losses of hot water tanks."""

    name = "brown2018"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Synergies of sector coupling and transmission reinforcement in a "
                "cost-optimised, highly renewable European energy system"
            ),
            author=[
                "Brown, T.",
                "Schlachtberger, D.",
                "Kies, A.",
                "Schramm, S.",
                "Greiner, M.",
            ],
            publication="Energy",
            publication_year=2018,
            doi="10.1016/j.energy.2018.06.222",
            note="Table 1 and Section 3, hot water tanks.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "industry" / "Brown2018_Table1.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path, index_col="technology")

    @staticmethod
    def hourly_self_discharge(tau_days: float) -> float:
        """Hourly loss for decay time constant tau."""
        return 1 - math.exp(-1 / (24 * tau_days))

    def get_self_discharge(self, element: IndustryTES, technology: str) -> Attribute:
        """Self-discharge of the storage type."""
        tau_days = float(self.data.at[technology, "tau_days"])
        self_discharge = self.hourly_self_discharge(tau_days)
        return element.self_discharge.set_data(
            default_value=self_discharge,
            unit="1",
            source=SourceInformation(
                description=f"{technology}, tau = {tau_days:g} days.",
                metadata=self.metadata,
            ),
        )
