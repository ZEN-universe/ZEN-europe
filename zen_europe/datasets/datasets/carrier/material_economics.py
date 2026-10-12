from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class MaterialEconomics(Dataset[dict[str, pd.DataFrame]]):
    """
    Material economics dataset class.

    This class implements the specific behavior for the Material Economics dataset.
    """

    _CARBON_INTENSITY_CEMENT_KILN = 0.54  # tCO2/tproduct
    name = "material_economics"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Industrial Transformation 2050 - "
                "Pathways to Net-Zero Emissions from EU Heavy Industry"
            ),
            author=["Material Economics"],
            publication="Material Economics",
            publication_year=2019,
            url="https://materialeconomics.com/publications/publication/industrial-transformation-2050",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        # TODO there is no data to be implemented
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    def get_secondary_steel_ratios(self) -> tuple[float, float]:
        """
        Get the secondary steel ratios.

        This method retrieves the secondary steel ratios at the beginning and the end
        and returns them as a tuple of floats.

        The share at the beginning is measured from the screen.
        The share at the end is chosen between 50% (CCS pathway) and 70% (circular
        economy)

        Returns:
            A tuple of floats representing the secondary steel ratios.
        """
        secondary_steel_share_beginning = 1 - 2.7 / 3.5
        secondary_steel_share_end = 0.6
        return (secondary_steel_share_beginning, secondary_steel_share_end)

    def get_clinker_carbon_intensity(self, element: ConversionTechnology) -> Attribute:
        """
        Get the clinker carbon intensity.

        This method retrieves the clinker carbon intensity and returns it as an
        Attribute.

        unit: tonCO2/tproduct

        Returns:
            An Attribute object representing the clinker carbon intensity.
        """
        attr = element.carbon_intensity_technology
        attr.set_data(
            default_value=self._CARBON_INTENSITY_CEMENT_KILN,
            unit="ton/tproduct",
            source=SourceInformation(
                description=(
                    "The clinker carbon intensity is based on Material Economics "
                    "(2019), 'Industrial Transformation 2050' "
                    "(https://materialeconomics.com/publications/publication/"
                    "industrial-transformation-2050)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_fuel_consumption_cement_kiln(self) -> float:
        """
        Get the fuel consumption for cement kilns.

        This method retrieves the fuel consumption for cement kilns and returns it as a
        float.

        unit: GJ/tproduct

        Returns:
            A float representing the fuel consumption for cement kilns.
        """
        return 3.7
