from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class LNGTerminalsZeal(Dataset[dict[str, pd.DataFrame]]):
    """
    LNG terminal construction dataset class from Zeal (2019).

    Provides the typical construction time of LNG import terminals reported in
    the industry literature.
    """

    name = "lng_terminals_zeal"

    CONSTRUCTION_TIME = 4

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Are LNG liquefication projects taking longer to construct?",
            author=["Tom Zeal"],
            publication="LNG 2019",
            publication_year=2019,
            url=(
                "https://www.almendron.com/tribuna/wp-content/uploads/2022/05/"
                "40-lng19-04april2019-zeal-tom-paper.pdf"
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
    def get_construction_time(self, technology: ConversionTechnology) -> Attribute:
        """
        Get the construction time of LNG terminals.
        """
        attr = technology.construction_time
        return attr.set_data(
            default_value=self.CONSTRUCTION_TIME,
            source=SourceInformation(
                description=(
                    f"The construction time of {technology.name} is set to "
                    f"{self.CONSTRUCTION_TIME} years, based on the typical "
                    "construction time of LNG import terminals reported in the "
                    "industry literature."
                ),
                metadata=self.metadata,
            ),
        )
