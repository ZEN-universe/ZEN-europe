from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, SourceInformation, TransportTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants


class ECProjectsOfCommonInterest(Dataset[dict[str, pd.DataFrame]]):
    """
    Dataset class for the first list of Projects of Common Interest and
    Projects of Mutual Interest of the European Commission.

    Provides the transport capacity of the first hydrogen pipeline projects,
    which sizes the capacity addition that is exempt from the diffusion limit.
    """

    name = "ec_pci_pmi_list"

    # daily transport capacity of the Mosahyc hydrogen pipeline, in GWh/day
    CAPACITY_PROJECT = {
        "hydrogen_pipeline": 5.5,
    }
    PROJECT_NAMES = {
        "hydrogen_pipeline": "Mosahyc",
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Technical document accompanying the first list of Projects of "
                "Common Interest and Projects of Mutual Interest"
            ),
            author=["European Commission"],
            publication="European Commission",
            publication_year=2024,
            url=(
                "https://energy.ec.europa.eu/document/download/"
                "944b96b9-4efd-44a3-bbfe-45b752b0b55f_en"
            ),
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
    def get_capacity_addition_unbounded(
        self, technology: TransportTechnology
    ) -> Attribute:
        """
        Get the unbounded capacity addition of a transport technology.
        """
        if technology.name not in self.CAPACITY_PROJECT:
            raise ValueError(
                f"The capacity of a first project of technology "
                f"'{technology.name}' is not available in the dataset "
                f"'{self.name}'."
            )
        capacity_project = self.CAPACITY_PROJECT[technology.name]
        project_name = self.PROJECT_NAMES[technology.name]
        attr = technology.capacity_addition_unbounded
        return attr.set_data(
            default_value=capacity_project / Constants.HOURS_PER_DAY,
            unit="GW",
            source=SourceInformation(
                description=(
                    "The unbounded capacity addition is the size of the "
                    f"{project_name} pipeline ({capacity_project} GWh per day)."
                ),
                metadata=self.metadata,
            ),
        )
