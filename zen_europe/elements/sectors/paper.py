from zen_creator import Sector

from zen_europe.elements.carriers.heat_industry import (
    HeatIndustry0100Paper,
    HeatIndustry100150Paper,
    HeatIndustry150200Paper,
)
from zen_europe.elements.carriers.industry_products import Paper
from zen_europe.elements.conversion_technologies.boiler_industry import (
    BiomassBoilerIndustryPaper,
    CoalBoilerIndustryPaper,
    ElectrodeBoilerIndustryPaper,
    NaturalGasBoilerIndustryPaper,
    OilBoilerIndustryPaper,
    WasteBoilerIndustryPaper,
)
from zen_europe.elements.conversion_technologies.heat_industry_temp_conversion import (
    HeatIndustryTempConversion100Paper,
    HeatIndustryTempConversion150Paper,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry import (
    HeatPumpIndustry0100WasteHeatPaper,
    HeatPumpIndustry0100WaterPaper,
    HeatPumpIndustry100150WasteHeatPaper,
    HeatPumpIndustry100150WaterPaper,
    HeatPumpIndustry150200WasteHeatPaper,
    HeatPumpIndustry150200WaterPaper,
)
from zen_europe.elements.conversion_technologies.industry_production import (
    PaperProduction,
)
from zen_europe.elements.storage_technologies.industry_DSM import PaperDSM
from zen_europe.elements.storage_technologies.industry_TES import (
    IndustryTESSteam150200Paper,
    IndustryTESWater0100Paper,
    IndustryTESWater100150Paper,
)


class PaperSector(Sector):
    """Paper production and its process heat supply.

    The sector has its own heat carriers and heat technologies, so heat is never
    shared with the other industry sectors.
    """

    name = "paper"
    required_sectors = [
        "electricity",
        "gas",
        "district_heating",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Paper,
            PaperProduction,
            HeatIndustry0100Paper,
            HeatIndustry100150Paper,
            HeatIndustry150200Paper,
            HeatPumpIndustry0100WasteHeatPaper,
            HeatPumpIndustry0100WaterPaper,
            HeatPumpIndustry100150WasteHeatPaper,
            HeatPumpIndustry100150WaterPaper,
            HeatPumpIndustry150200WasteHeatPaper,
            HeatPumpIndustry150200WaterPaper,
            BiomassBoilerIndustryPaper,
            ElectrodeBoilerIndustryPaper,
            NaturalGasBoilerIndustryPaper,
            OilBoilerIndustryPaper,
            CoalBoilerIndustryPaper,
            WasteBoilerIndustryPaper,
            HeatIndustryTempConversion150Paper,
            HeatIndustryTempConversion100Paper,
            IndustryTESWater0100Paper,
            IndustryTESWater100150Paper,
            IndustryTESSteam150200Paper,
            PaperDSM,
        ]
