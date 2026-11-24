from zen_creator import Sector

from zen_europe.elements.carriers.paper import Paper
from zen_europe.elements.conversion_technologies.paper_production import (
    PaperProduction,
)


class PaperSector(Sector):
    """Paper production.

    The process heat below 200 °C comes from the shared `industrial_heat` sector.
    """

    name = "paper"
    required_sectors = [
        "electricity",
        "gas",
        "district_heating",
        "industrial_heat",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Paper,
            PaperProduction,
        ]
