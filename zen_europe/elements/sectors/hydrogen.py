from zen_creator import Sector

from zen_europe.elements.carriers.biomethane import Biomethane
from zen_europe.elements.carriers.hydrogen import Hydrogen
from zen_europe.elements.carriers.wet_biomass import WetBiomass
from zen_europe.elements.conversion_technologies.anaerobic_digestion import (
    AnaerobicDigestion,
)
from zen_europe.elements.conversion_technologies.biomethane_conversion import (
    BiomethaneConversion,
)
from zen_europe.elements.conversion_technologies.electrolysis import Electrolysis
from zen_europe.elements.conversion_technologies.fischer_tropsch import FischerTropsch
from zen_europe.elements.conversion_technologies.fuel_cell import FuelCell
from zen_europe.elements.conversion_technologies.gasification import Gasification
from zen_europe.elements.conversion_technologies.H2_DRI import H2_DRI
from zen_europe.elements.conversion_technologies.HDT_FCEV import HDT_FCEV
from zen_europe.elements.conversion_technologies.hydrogen_FC_ship import (
    HydrogenFCShip,
)
from zen_europe.elements.conversion_technologies.methanation import Methanation
from zen_europe.elements.conversion_technologies.SMR import SMR
from zen_europe.elements.retrofitting_technologies.hydrogen_to_cement_fuel import (
    HydrogenToCementFuel,
)
from zen_europe.elements.retrofitting_technologies.SMR_CCS import SMR_CCS
from zen_europe.elements.storage_technologies.salt_cavern_storage import (
    SaltCavernStorage,
)
from zen_europe.elements.transport_technologies.hydrogen_pipeline import (
    HydrogenPipeline,
)


class HydrogenSector(Sector):
    """Hydrogen production, storage and transport, and its direct derivatives."""

    name = "hydrogen"
    required_sectors = ["electricity", "heat", "district_heating", "gas"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Electrolysis,
            FuelCell,
            SMR,
            Gasification,
            AnaerobicDigestion,
            BiomethaneConversion,
            FischerTropsch,
            Methanation,
            HydrogenPipeline,
            SaltCavernStorage,
            SMR_CCS,
            HDT_FCEV,
            HydrogenToCementFuel,
            HydrogenFCShip,
            H2_DRI,
            Hydrogen,
            Biomethane,
            WetBiomass,
        ]
