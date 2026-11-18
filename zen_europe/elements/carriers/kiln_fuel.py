# TODO: Jacob decide how to model this. Should be one element per module.
from zen_creator.elements import Carrier

from zen_europe.elements.carriers.heat_industry import HeatIndustry


class KilnFuelGlass(HeatIndustry, Carrier):
    name: str = "kiln_fuel_glass"


class KilnFuelCeramic(HeatIndustry, Carrier):
    name: str = "kiln_fuel_ceramic"
