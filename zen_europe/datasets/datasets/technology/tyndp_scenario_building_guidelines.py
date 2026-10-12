from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from zen_creator import Attribute, SourceInformation, TransportTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class TYNDPScenarioBuildingGuidelines(Dataset[dict[str, pd.DataFrame]]):
    """
    Pipeline cost dataset class from the TYNDP 2022 scenario building
    guidelines.

    Provides the distance-specific investment cost of gas pipelines reported in
    Tab. 14, p. 32, which is also applied to the other pipelines transporting
    liquid or gaseous fuels.
    """

    name = "tyndp_scenario_building_guidelines"

    CAPEX_PER_DISTANCE = {
        "natural_gas_pipeline": 265,
        "oil_pipeline": 265,
    }
    CAPEX_PER_DISTANCE_UNIT = "kiloEuro/GW/km"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="TYNDP 2022 Scenario Building Guidelines",
            author=["ENTSOG", "ENTSO-E"],
            publication="ENTSOG and ENTSO-E",
            publication_year=2021,
            url=(
                "https://www.entsog.eu/sites/default/files/2021-10/"
                "entsos_TYNDP_2022_Scenario_Building_Guidelines_211007_1.pdf"
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
    def get_capex_per_distance_transport(
        self, technology: TransportTechnology
    ) -> Attribute:
        """
        Get the distance-specific capex of a transport technology.
        """
        if technology.name not in self.CAPEX_PER_DISTANCE:
            raise ValueError(
                f"The distance-specific capex of technology "
                f"'{technology.name}' is not available in the dataset "
                f"'{self.name}'."
            )
        attr = technology.capex_per_distance_transport
        return attr.set_data(
            default_value=self.CAPEX_PER_DISTANCE[technology.name],
            unit=self.CAPEX_PER_DISTANCE_UNIT,
            source=SourceInformation(
                description=(
                    f"The investment cost of {technology.name} is based on the "
                    "gas pipeline investment cost of the TYNDP 2022 scenario "
                    "building guidelines (Tab. 14, p. 32)."
                ),
                metadata=self.metadata,
            ),
        )
