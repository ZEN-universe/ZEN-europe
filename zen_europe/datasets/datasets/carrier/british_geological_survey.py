from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class BritishGeologicalSurvey(Dataset[pd.DataFrame]):
    """
    British Geological Survey dataset class.

    This class implements the specific behavior for the British Geological Survey
    dataset.
    """

    name = "british_geological_survey"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("World Mineral Production 2017 - 2021"),
            author=[
                "N E Idoine",
                "E R Raycraft",
                "F Price",
                "S F Hobbs",
                "E A Deady",
                "P Everett",
                "R A Shaw",
                "E J Evans",
                "A J Mills ",
            ],
            publication="British Geological Survey",
            publication_year=2023,
            url="https://www.bgs.ac.uk/news/world-mineral-production-2017-to-2021-is-now-available/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """Sets the manual data for the British Geological Survey dataset.

        Values are in kt/y in 2021.
        """
        return pd.Series({"UK": 9008, "CH": 4180, "NO": 1780})

    # -------- methods ------------------------
    def get_manual_cement_demand(self, node: str) -> int:
        """
        Get the demand of cement from the British Geological Survey dataset.

        Returns the demand in kt/y for the given node.

        Args:
            node: The node for which to get the demand.

        Returns:
            The demand in kt/y for the given node.
        """
        if node in self.data.index:
            return self.data.loc[node]
        else:
            raise ValueError(
                f"Node {node} not found in the manual values of the"
                f" British Geological Survey dataset."
            )
