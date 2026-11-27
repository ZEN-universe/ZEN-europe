from zen_creator import Sector

from zen_europe.elements.carriers.biomass import Biomass
from zen_europe.elements.carriers.electricity import Electricity
from zen_europe.elements.carriers.hard_coal import HardCoal
from zen_europe.elements.carriers.lignite import Lignite
from zen_europe.elements.carriers.oil import Oil
from zen_europe.elements.carriers.uranium import Uranium
from zen_europe.elements.carriers.waste import Waste
from zen_europe.elements.conversion_technologies.biomass_plant import BiomassPlant
from zen_europe.elements.conversion_technologies.hard_coal_plant import HardCoalPlant
from zen_europe.elements.conversion_technologies.lignite_coal_plant import (
    LigniteCoalPlant,
)
from zen_europe.elements.conversion_technologies.natural_gas_turbine import (
    NaturalGasTurbine,
)
from zen_europe.elements.conversion_technologies.nuclear import Nuclear
from zen_europe.elements.conversion_technologies.oil_plant import OilPlant
from zen_europe.elements.conversion_technologies.photovoltaics_rooftop import (
    PhotovoltaicsRooftop,
)
from zen_europe.elements.conversion_technologies.photovoltaics_utility import (
    PhotovoltaicsUtility,
)
from zen_europe.elements.conversion_technologies.run_of_river_hydro import (
    RunOfRiverHydro,
)
from zen_europe.elements.conversion_technologies.waste_plant import WastePlant
from zen_europe.elements.conversion_technologies.wind_offshore import WindOffshore
from zen_europe.elements.conversion_technologies.wind_onshore import WindOnshore
from zen_europe.elements.retrofitting_technologies.biomass_plant_CCS import (
    BiomassPlantCCS,
)
from zen_europe.elements.retrofitting_technologies.natural_gas_turbine_CCS import (
    NaturalGasTurbineCCS,
)
from zen_europe.elements.storage_technologies.battery import Battery
from zen_europe.elements.storage_technologies.pumped_hydro import PumpedHydro
from zen_europe.elements.storage_technologies.reservoir_hydro import ReservoirHydro
from zen_europe.elements.transport_technologies.power_line import PowerLine


class ElectricitySector(Sector):
    """Electricity generation, storage and transmission."""

    name = "electricity"
    required_sectors = ["gas"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            PhotovoltaicsUtility,
            PhotovoltaicsRooftop,
            WindOnshore,
            WindOffshore,
            HardCoalPlant,
            NaturalGasTurbine,
            Nuclear,
            RunOfRiverHydro,
            LigniteCoalPlant,
            BiomassPlant,
            OilPlant,
            WastePlant,
            NaturalGasTurbineCCS,
            BiomassPlantCCS,
            Battery,
            PumpedHydro,
            ReservoirHydro,
            PowerLine,
            Electricity,
            HardCoal,
            Uranium,
            Lignite,
            Biomass,
            Oil,
            Waste,
        ]
