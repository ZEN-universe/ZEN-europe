from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import AssumptionInformation, MetaData
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_creator import Element

# offset between degrees Celsius and Kelvin
KELVIN = 273.15


class IndustryGeneralAssumptions(Dataset[pd.DataFrame]):
    """
    General assumptions of the industry sectors.

    Heat pump COP, waste-heat recovery cost, process CO2, kiln fuel switching, and
    the technical assumptions of the temperature cascade, TES and DSM.
    """

    name = "industry_general_assumptions"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="General assumptions of the industry sectors",
            author=["Goericke, H."],
            publication="docs/files/user_guide/industry.md",
            publication_year=2026,
            note="The reasoning of each value is given in the description column.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "03-technology"
            / "industry"
            / "general_assumptions_industries.csv"
        )

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_csv(
            self.path, keep_default_na=False, float_precision="round_trip"
        )
        return data.set_index(["parameter", "key"])

    def has_value(self, parameter: str, key: str = "") -> bool:
        """Whether an assumption exists, e.g. a kiln switchable share of a sector."""
        return (parameter, key) in self.data.index

    def get_value(self, parameter: str, key: str = "") -> float:
        """Value of an assumption, in the unit of the unit column."""
        return float(self.data.at[(parameter, key), "value"])

    def get_unit(self, parameter: str, key: str = "") -> str:
        """Unit of an assumption."""
        return str(self.data.at[(parameter, key), "unit"])

    def get_description(self, parameter: str, key: str = "") -> str:
        """Reasoning and sources of an assumption."""
        return str(self.data.at[(parameter, key), "description"])

    def get_attribute(
        self, element: Element, attribute: str, parameter: str, key: str = ""
    ) -> Attribute:
        """Set the attribute `attribute` of the element to an assumption."""
        return getattr(element, attribute).set_data(
            default_value=self.get_value(parameter, key),
            unit=self.get_unit(parameter, key),
            source=AssumptionInformation(
                description=self.get_description(parameter, key)
            ),
        )

    def get_conversion_factor_heat_pump(self, element: Element) -> Attribute:
        """Electricity per heat of an industrial heat pump, from a fraction of the
        Carnot COP between the heat source and the centre of the band."""
        carnot_efficiency = self.get_value("carnot_efficiency")
        supply = self.get_value("supply_temperature", element.temp_level)
        source = self.get_value("source_temperature", element.heat_source)
        cop = round(carnot_efficiency * supply / (supply - source), 4)
        return element.conversion_factor.set_data(
            default_value=[
                {
                    "electricity": {
                        "default_value": round(1.0 / cop, 12),
                        "unit": "GW/GW",
                    }
                }
            ],
            source=AssumptionInformation(
                description=(
                    f"The COP of {cop} is {carnot_efficiency:.0%} of the Carnot COP "
                    f"between the source ({source - KELVIN:.0f} °C) and the centre "
                    f"of the temperature band ({supply - KELVIN:.0f} °C). "
                    + self.get_description("carnot_efficiency")
                ),
            ),
        )
