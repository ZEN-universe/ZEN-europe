from zen_creator import Sector

from zen_europe.elements.carriers.heat_industry import (
    HeatIndustry0100Food,
    HeatIndustry100150Food,
    HeatIndustry150200Food,
)
from zen_europe.elements.carriers.industry_products import Food
from zen_europe.elements.conversion_technologies.boiler_industry import (
    BiomassBoilerIndustryFood,
    CoalBoilerIndustryFood,
    ElectrodeBoilerIndustryFood,
    NaturalGasBoilerIndustryFood,
    OilBoilerIndustryFood,
    WasteBoilerIndustryFood,
)
from zen_europe.elements.conversion_technologies.heat_industry_temp_conversion import (
    HeatIndustryTempConversion100Food,
    HeatIndustryTempConversion150Food,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry import (
    HeatPumpIndustry0100WasteHeatFood,
    HeatPumpIndustry0100WaterFood,
    HeatPumpIndustry100150WasteHeatFood,
    HeatPumpIndustry100150WaterFood,
    HeatPumpIndustry150200WasteHeatFood,
    HeatPumpIndustry150200WaterFood,
)
from zen_europe.elements.conversion_technologies.industry_production import (
    FoodProduction,
)
from zen_europe.elements.storage_technologies.industry_DSM import FoodDSM
from zen_europe.elements.storage_technologies.industry_TES import (
    IndustryTESSteam150200Food,
    IndustryTESWater0100Food,
    IndustryTESWater100150Food,
)


class FoodSector(Sector):
    """Food production and its process heat supply.

    The sector has its own heat carriers and heat technologies, so heat is never
    shared with the other industry sectors.
    """

    name = "food"
    required_sectors = [
        "electricity",
        "gas",
        "district_heating",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Food,
            FoodProduction,
            HeatIndustry0100Food,
            HeatIndustry100150Food,
            HeatIndustry150200Food,
            HeatPumpIndustry0100WasteHeatFood,
            HeatPumpIndustry0100WaterFood,
            HeatPumpIndustry100150WasteHeatFood,
            HeatPumpIndustry100150WaterFood,
            HeatPumpIndustry150200WasteHeatFood,
            HeatPumpIndustry150200WaterFood,
            BiomassBoilerIndustryFood,
            ElectrodeBoilerIndustryFood,
            NaturalGasBoilerIndustryFood,
            OilBoilerIndustryFood,
            CoalBoilerIndustryFood,
            WasteBoilerIndustryFood,
            HeatIndustryTempConversion150Food,
            HeatIndustryTempConversion100Food,
            IndustryTESWater0100Food,
            IndustryTESWater100150Food,
            IndustryTESSteam150200Food,
            FoodDSM,
        ]
