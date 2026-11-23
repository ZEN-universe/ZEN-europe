from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import class_attribute

if TYPE_CHECKING:
    from zen_creator import ConversionTechnology


class Bever2024(Dataset[pd.Series]):
    """
    Dataset class for the coefficient of performance (COP) of industrial
    high-temperature heat pumps from Bever et al. (2024).

    The COP is a fraction of the Carnot COP between the source temperature of the
    heat source and the supply temperature of the temperature band.
    """

    name = "bever2024"

    # fraction of the Carnot COP that industrial high-temperature heat pumps reach
    CARNOT_EFFICIENCY = 0.5
    # supply temperature per temperature band (°C): the centre of the band
    SUPPLY_TEMPERATURE = {"0_100": 75.0, "100_150": 125.0, "150_200": 175.0}
    # source temperature per heat source (°C); waste heat as in Agora Energiewende and
    # Fraunhofer IEG (2023), Roll-out von Großwärmepumpen in Deutschland
    SOURCE_TEMPERATURE = {"waste_heat": 50.0, "water": 15.0}

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="High-Temperature Heat Pumps for Industrial Use",
            author=[
                "Paul-Michael Bever",
                "Frédéric Bless",
                "Cordin Arpagaus",
                "Stefan S. Bertsch",
            ],
            publication="Chemie Ingenieur Technik 96(8), 1071-1084",
            publication_year=2024,
            url="https://doi.org/10.1002/cite.202300241",
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
    def get_cop(self, temp_level: str, heat_source: str) -> float:
        """
        Get the COP of an industrial heat pump supplying the temperature band
        `temp_level` from the heat source `heat_source`.

        Returns:
            float: The fraction of the Carnot COP between the source and the supply
                temperature.
        """
        if temp_level not in self.SUPPLY_TEMPERATURE:
            raise ValueError(f"Supply temperature of {temp_level} is not defined.")
        if heat_source not in self.SOURCE_TEMPERATURE:
            raise ValueError(f"Source temperature of {heat_source} is not defined.")
        supply = self.SUPPLY_TEMPERATURE[temp_level] + Constants.KELVIN_AT_ZERO_CELSIUS
        source = self.SOURCE_TEMPERATURE[heat_source] + Constants.KELVIN_AT_ZERO_CELSIUS
        return round(self.CARNOT_EFFICIENCY * supply / (supply - source), 4)

    def get_conversion_factor_heat_pump(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the electricity per heat of an industrial heat pump: the inverse of the
        COP of its temperature band and heat source.

        Returns:
            Attribute: An Attribute object containing the conversion factor.
        """
        temp_level = class_attribute(element, "temp_level")
        heat_source = class_attribute(element, "heat_source")
        cop = self.get_cop(temp_level, heat_source)
        return element.conversion_factor.set_data(
            default_value=[
                {
                    "electricity": {
                        "default_value": round(1.0 / cop, 12),
                        "unit": "GW/GW",
                    }
                }
            ],
            source=SourceInformation(
                description=(
                    f"The COP of {cop} is {self.CARNOT_EFFICIENCY:.0%} of the Carnot "
                    "COP between the heat source "
                    f"({self.SOURCE_TEMPERATURE[heat_source]:.0f} °C) and the "
                    "centre of the temperature band "
                    f"({self.SUPPLY_TEMPERATURE[temp_level]:.0f} °C), based "
                    "on Bever et al. (2024); the waste heat temperature is based on "
                    "Agora Energiewende and Fraunhofer IEG (2023), Roll-out von "
                    "Großwärmepumpen in Deutschland."
                ),
                metadata=self.metadata,
            ),
        )
