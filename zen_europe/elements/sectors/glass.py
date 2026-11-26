from zen_creator import Sector

from zen_europe.elements.carriers.glass import Glass
from zen_europe.elements.carriers.glass_fuel import GlassFuel
from zen_europe.elements.conversion_technologies.glass_production import (
    GlassProduction,
)
from zen_europe.elements.retrofitting_technologies.electricity_to_glass_fuel import (
    ElectricityToGlassFuel,
)
from zen_europe.elements.retrofitting_technologies.glass_post_comb import (
    GlassPostComb,
)
from zen_europe.elements.retrofitting_technologies.hydrogen_to_glass_fuel import (
    HydrogenToGlassFuel,
)
from zen_europe.elements.retrofitting_technologies.natural_gas_to_glass_fuel import (
    NaturalGasToGlassFuel,
)


class GlassSector(Sector):
    """Glass production and the fuel of its furnaces.

    The process heat below 200 °C comes from the shared `industrial_heat` sector.
    """

    name = "glass"
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
            Glass,
            GlassProduction,
            GlassPostComb,
            GlassFuel,
            NaturalGasToGlassFuel,
            HydrogenToGlassFuel,
            ElectricityToGlassFuel,
        ]
