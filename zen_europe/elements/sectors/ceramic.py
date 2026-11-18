from zen_creator import Sector

from zen_europe.elements.carriers.heat_industry import (
    HeatIndustry0100Ceramic,
    HeatIndustry100150Ceramic,
    HeatIndustry150200Ceramic,
)
from zen_europe.elements.carriers.industry_products import Ceramic
from zen_europe.elements.carriers.kiln_fuel import KilnFuelCeramic
from zen_europe.elements.conversion_technologies.boiler_industry import (
    BiomassBoilerIndustryCeramic,
    CoalBoilerIndustryCeramic,
    ElectrodeBoilerIndustryCeramic,
    NaturalGasBoilerIndustryCeramic,
    OilBoilerIndustryCeramic,
    WasteBoilerIndustryCeramic,
)
from zen_europe.elements.conversion_technologies.heat_industry_temp_conversion import (
    HeatIndustryTempConversion100Ceramic,
    HeatIndustryTempConversion150Ceramic,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry import (
    HeatPumpIndustry0100WasteHeatCeramic,
    HeatPumpIndustry0100WaterCeramic,
    HeatPumpIndustry100150WasteHeatCeramic,
    HeatPumpIndustry100150WaterCeramic,
    HeatPumpIndustry150200WasteHeatCeramic,
    HeatPumpIndustry150200WaterCeramic,
)
from zen_europe.elements.conversion_technologies.industry_production import (
    CeramicProduction,
)
from zen_europe.elements.conversion_technologies.kiln_fuel_industry import (
    ElectricityToKilnFuelCeramic,
    HydrogenToKilnFuelCeramic,
    NaturalGasToKilnFuelCeramic,
)
from zen_europe.elements.retrofitting_technologies.industry_post_comb import (
    CeramicPostComb,
)
from zen_europe.elements.storage_technologies.industry_DSM import CeramicDSM
from zen_europe.elements.storage_technologies.industry_TES import (
    IndustryTESSteam150200Ceramic,
    IndustryTESWater0100Ceramic,
    IndustryTESWater100150Ceramic,
)


class CeramicSector(Sector):
    """Ceramic production and its process heat supply.

    The sector has its own heat carriers and heat technologies, so heat is never
    shared with the other industry sectors.
    """

    name = "ceramic"
    required_sectors = [
        "electricity",
        "gas",
        "hydrogen",
        "district_heating",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Ceramic,
            CeramicProduction,
            CeramicPostComb,
            HeatIndustry0100Ceramic,
            HeatIndustry100150Ceramic,
            HeatIndustry150200Ceramic,
            KilnFuelCeramic,
            HeatPumpIndustry0100WasteHeatCeramic,
            HeatPumpIndustry0100WaterCeramic,
            HeatPumpIndustry100150WasteHeatCeramic,
            HeatPumpIndustry100150WaterCeramic,
            HeatPumpIndustry150200WasteHeatCeramic,
            HeatPumpIndustry150200WaterCeramic,
            BiomassBoilerIndustryCeramic,
            ElectrodeBoilerIndustryCeramic,
            NaturalGasBoilerIndustryCeramic,
            OilBoilerIndustryCeramic,
            CoalBoilerIndustryCeramic,
            WasteBoilerIndustryCeramic,
            HeatIndustryTempConversion150Ceramic,
            HeatIndustryTempConversion100Ceramic,
            NaturalGasToKilnFuelCeramic,
            HydrogenToKilnFuelCeramic,
            ElectricityToKilnFuelCeramic,
            IndustryTESWater0100Ceramic,
            IndustryTESWater100150Ceramic,
            IndustryTESSteam150200Ceramic,
            CeramicDSM,
        ]
