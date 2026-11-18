from zen_creator import Sector

from zen_europe.elements.carriers.clinker import Clinker
from zen_europe.elements.carriers.fuel_for_cement import FuelForCement
from zen_europe.elements.conversion_technologies.cement_kiln import CementKiln
from zen_europe.elements.retrofitting_technologies.biomass_to_cement_fuel import (
    BiomassToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.cement_post_comb import (
    CementPostComb,
)
from zen_europe.elements.retrofitting_technologies.coal_to_cement_fuel import (
    CoalToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.hydrogen_to_cement_fuel import (
    HydrogenToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.industry_post_comb import (
    CeramicPostComb,
    GlassPostComb,
)
from zen_europe.elements.retrofitting_technologies.waste_to_cement_fuel import (
    WasteToCementFuel,
)
from zen_europe.elements.storage_technologies.industry_DSM import ClinkerDSM


class CementSector(Sector):
    """Cement clinker production."""

    name = "cement"
    required_sectors = []

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            CementKiln,
            CoalToCementFuel,
            WasteToCementFuel,
            BiomassToCementFuel,
            HydrogenToCementFuel,
            CementPostComb,
            GlassPostComb,
            CeramicPostComb,
            Clinker,
            FuelForCement,
            ClinkerDSM,
        ]
