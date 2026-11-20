from zen_creator import Sector

from zen_europe.elements.carriers.cement_fuel import CementFuel
from zen_europe.elements.carriers.clinker import Clinker
from zen_europe.elements.conversion_technologies.cement_production import (
    CementProduction,
)
from zen_europe.elements.retrofitting_technologies.biomass_to_cement_fuel import (
    BiomassToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.cement_post_comb import (
    CementPostComb,
)
from zen_europe.elements.retrofitting_technologies.ceramic_post_comb import (
    CeramicPostComb,
)
from zen_europe.elements.retrofitting_technologies.coal_to_cement_fuel import (
    CoalToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.glass_post_comb import (
    GlassPostComb,
)
from zen_europe.elements.retrofitting_technologies.hydrogen_to_cement_fuel import (
    HydrogenToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.waste_to_cement_fuel import (
    WasteToCementFuel,
)


class CementSector(Sector):
    """Cement clinker production."""

    name = "cement"
    required_sectors = ["industrial_heat"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            CementProduction,
            CoalToCementFuel,
            WasteToCementFuel,
            BiomassToCementFuel,
            HydrogenToCementFuel,
            CementPostComb,
            GlassPostComb,
            CeramicPostComb,
            Clinker,
            CementFuel,
        ]
