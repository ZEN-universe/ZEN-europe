from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import Attribute, Carrier
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.utils.constants import Constants


class IPCCEmissionFactors(Dataset[pd.Series]):
    """
    IPCC emission factors dataset.

    This class implements the specific behavior for the IPCC emission factors dataset.
    """

    name = "ipcc_emission_factors"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "2006 IPCC Guidelines for National Greenhouse Gas Inventories - Volume "
                "2: Energy"
            ),
            author=["IPCC"],
            publication="2006 IPCC Guidelines for National Greenhouse Gas Inventories",
            publication_year=2006,
            url="https://www.ipcc-nggip.iges.or.jp/public/2006gl/",
            note="Introduction, Table 1.4",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """sets the data for the IPCC emission factors dataset from kg/TJ to
        tons/MWh."""
        conversion_factor = Constants.GJ_PER_MWH / 1000 / 1000  # from kg/TJ to tons/MWh
        data = {}

        data["oil"] = 74100 * conversion_factor  # Gas/Diesel Oil
        data["crude_oil"] = 73300 * conversion_factor  # Crude Oil
        data["natural_gas"] = 56100 * conversion_factor  # Natural Gas
        data["lng"] = 56100 * conversion_factor  # Natural Gas
        data["gasoline"] = 69300 * conversion_factor  # Motor Gasoline
        data["diesel"] = 74100 * conversion_factor  # Gas/Diesel Oil
        data["waste"] = (
            91700 * conversion_factor
        )  # Municipal Wastes (non-biomass fraction)
        data["hard_coal"] = (
            94600 * conversion_factor
        )  # Coking Coal/Other bituminous Coal
        data["lignite"] = 101000 * conversion_factor  # Lignite
        data["biomass"] = 112000 * conversion_factor  # Wood/Wood Waste
        data["biogas"] = 54600 * conversion_factor  # Landfill/Sludge/Other Biogas

        return pd.Series(data)

    # -------- methods ------------------------
    def _get_raw_carbon_intensity(self, element: Carrier) -> float:
        """
        Get the raw carbon intensity of a specific element.

        Returns the carbon intensity in tons/MWh for the given element.

        Args:
            element: The element for which to get the carbon intensity.
        """
        if element.name not in self.data.index:
            raise ValueError(
                f"Carbon intensity for {element.name}"
                " is not available in the IPCC emission factors dataset."
            )
        return self.data.loc[element.name]

    def get_carbon_intensity(self, element: Carrier) -> Attribute:
        """
        Get the carbon intensity of a specific element.

        Returns the carbon intensity in tons/MWh for the given element.

        Args:
            element: The element for which to get the carbon intensity.

        Returns:
            The carbon intensity in kg/MWh for the given element.
        """
        default_value = self._get_raw_carbon_intensity(element)
        source = SourceInformation(
            description=(
                f"Carbon intensity of {element.name} from the IPCC emission factors "
                "dataset, converted from kgCO2/TJ to tonsCO2/MWh."
            ),
            metadata=self.metadata,
        )
        return element.carbon_intensity_carrier_import.set_data(
            source=source,
            default_value=default_value,
            unit="ton/MWh",
        )

    def get_unit(self) -> str:
        """
        Get the unit of the IPCC emission factors dataset.

        Returns:
            The unit of the dataset, which is "tons/MWh".
        """
        return "tons/MWh"
