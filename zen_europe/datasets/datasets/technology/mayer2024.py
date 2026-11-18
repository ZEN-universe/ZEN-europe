from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_europe.elements.storage_technologies.industry_TES import IndustryTES


class Mayer2024(Dataset[pd.DataFrame]):
    """Costs and lifetimes of thermal energy storage technologies."""

    name = "mayer2024"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Flexibility from industrial demand-side management in net-zero "
                "sector-coupled national energy systems"
            ),
            author=[
                "Mayer, P.",
                "Heer, M.",
                "Shu, D. Y.",
                "Zielonka, N.",
                "Leenders, L.",
                "Baader, F. J.",
                "Bardow, A.",
            ],
            publication="Frontiers in Energy Research",
            publication_year=2024,
            doi="10.3389/fenrg.2024.1443506",
            note="Table 3, thermal energy storage technologies.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "industry" / "Mayer2024_Table3.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path, index_col="technology")

    def get_lifetime(self, element: IndustryTES) -> Attribute:
        """Lifetime of the storage type."""
        return element.lifetime.set_data(
            default_value=float(self.data.at[element.storage_type, "lifetime_years"]),
            unit="1",
            source=SourceInformation(
                description=f"Lifetime of a {element.storage_type}.",
                metadata=self.metadata,
            ),
        )

    def get_capex_specific_storage_energy(self, element: IndustryTES) -> Attribute:
        """Investment cost of the storage type."""
        return element.capex_specific_storage_energy.set_data(
            default_value=float(
                self.data.at[element.storage_type, "invest_cost_EUR_kWh"]
            )
            * 1000.0,
            unit="Euro/MWh",
            source=SourceInformation(
                description=f"Investment cost of a {element.storage_type}.",
                metadata=self.metadata,
            ),
        )

    def get_opex_specific_fixed_energy(self, element: IndustryTES) -> Attribute:
        """Fixed O&M cost of the storage type."""
        return element.opex_specific_fixed_energy.set_data(
            default_value=float(
                self.data.at[element.storage_type, "fixed_OaM_cost_EUR_kWh"]
            )
            * 1000.0,
            unit="Euro/MWh",
            source=SourceInformation(
                description=f"Fixed O&M cost of a {element.storage_type}.",
                metadata=self.metadata,
            ),
        )
