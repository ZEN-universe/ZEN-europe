from zen_creator import Sector

from zen_europe.elements.carriers.ceramic import Ceramic
from zen_europe.elements.carriers.ceramic_fuel import CeramicFuel
from zen_europe.elements.conversion_technologies.ceramic_production import (
    CeramicProduction,
)
from zen_europe.elements.retrofitting_technologies.ceramic_post_comb import (
    CeramicPostComb,
)
from zen_europe.elements.retrofitting_technologies.electricity_to_ceramic_fuel import (
    ElectricityToCeramicFuel,
)
from zen_europe.elements.retrofitting_technologies.hydrogen_to_ceramic_fuel import (
    HydrogenToCeramicFuel,
)
from zen_europe.elements.retrofitting_technologies.natural_gas_to_ceramic_fuel import (
    NaturalGasToCeramicFuel,
)


class CeramicSector(Sector):
    """Ceramic production and the fuel of its kilns.

    The process heat below 200 °C comes from the shared `industrial_heat` sector.
    """

    name = "ceramic"
    required_sectors = [
        "electricity",
        "gas",
        "hydrogen",
        "district_heating",
        "industrial_heat",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Ceramic,
            CeramicProduction,
            CeramicPostComb,
            CeramicFuel,
            NaturalGasToCeramicFuel,
            HydrogenToCeramicFuel,
            ElectricityToCeramicFuel,
        ]
