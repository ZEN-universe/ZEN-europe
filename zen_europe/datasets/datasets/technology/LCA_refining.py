from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class LCARefining(Dataset[pd.Series]):
    """
    Dataset class for the life cycle costing and eeco-efficiency assessment of oil
    refining.

    """

    name = "lca_refining"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Life Cycle Costing and Eco-Efficiency Assessment of Fuel Production "
                "by Coprocessing Biomass in Crude Oil Refineries"
            ),
            author=["Pedro L. Cruz", "Diego Iribarren", "Javier Dufour"],
            publication="MDPI energies",
            publication_year=2019,
            url="https://www.mdpi.com/1996-1073/12/24/4664",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        data: dict[str, float] = {}
        return pd.Series(data)

    # -------- methods ------------------------
    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """
        Get the lifetime for refining technologies.

        Returns:
            Attribute: An Attribute object containing the lifetime data.
        """
        attr = element.lifetime
        lifetime = 30
        attr.set_data(
            default_value=lifetime,
            source=SourceInformation(
                description=(
                    "The lifetime for refining technologies is obtained from the life "
                    "cycle costing and eco-efficiency assessment dataset."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )
        return attr

    def get_construction_time(self, element: ConversionTechnology) -> Attribute:
        """
        Get the construction time for refining technologies.

        Returns:
            Attribute: An Attribute object containing the construction time data.
        """
        attr = element.construction_time
        construction_time = 3  # assumed construction time in years
        attr.set_data(
            default_value=construction_time,
            source=SourceInformation(
                description=(
                    "The construction time for refining technologies is obtained from "
                    "the life cycle costing and eco-efficiency assessment dataset."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )
        return attr
