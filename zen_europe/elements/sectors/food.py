from zen_creator import Sector

from zen_europe.elements.carriers.food import Food
from zen_europe.elements.conversion_technologies.food_production import (
    FoodProduction,
)


class FoodSector(Sector):
    """Food production.

    The process heat below 200 °C comes from the shared `industrial_heat` sector.
    """

    name = "food"
    required_sectors = [
        "electricity",
        "gas",
        "district_heating",
        "industrial_heat",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Food,
            FoodProduction,
        ]
