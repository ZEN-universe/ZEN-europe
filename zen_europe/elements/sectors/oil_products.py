from zen_creator import Sector

from zen_europe.elements.carriers.diesel import Diesel
from zen_europe.elements.carriers.gasoline import Gasoline
from zen_europe.elements.carriers.kerosene import Kerosene
from zen_europe.elements.carriers.naphtha import Naphtha


class OilProductsSector(Sector):
    """Diesel and gasoline used by transport. They are imported unless the
    refining sector produces them from crude oil."""

    name = "oil_products"
    required_sectors = []

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Diesel,
            Gasoline,
            Kerosene,
            Naphtha,
        ]
