from zen_creator import Sector

from zen_europe.elements.carriers.heat_industry_0_100 import HeatIndustry0100
from zen_europe.elements.carriers.heat_industry_100_150 import HeatIndustry100150
from zen_europe.elements.carriers.heat_industry_150_200 import HeatIndustry150200
from zen_europe.elements.carriers.recoverable_waste_heat import RecoverableWasteHeat
from zen_europe.elements.conversion_technologies.anaerobic_digestion import (
    AnaerobicDigestion,
)
from zen_europe.elements.conversion_technologies.BF_BOF import BF_BOF
from zen_europe.elements.conversion_technologies.biomass_boiler_industry import (
    BiomassBoilerIndustry,
)
from zen_europe.elements.conversion_technologies.biomethane_conversion import (
    BiomethaneConversion,
)
from zen_europe.elements.conversion_technologies.cement_production import (
    CementProduction,
)
from zen_europe.elements.conversion_technologies.ceramic_production import (
    CeramicProduction,
)
from zen_europe.elements.conversion_technologies.coal_boiler_industry import (
    CoalBoilerIndustry,
)
from zen_europe.elements.conversion_technologies.DAC import DAC
from zen_europe.elements.conversion_technologies.EAF import EAF
from zen_europe.elements.conversion_technologies.electrode_boiler_industry import (
    ElectrodeBoilerIndustry,
)
from zen_europe.elements.conversion_technologies.electrolysis import Electrolysis
from zen_europe.elements.conversion_technologies.fischer_tropsch import FischerTropsch
from zen_europe.elements.conversion_technologies.food_production import FoodProduction
from zen_europe.elements.conversion_technologies.gasification import Gasification
from zen_europe.elements.conversion_technologies.glass_production import (
    GlassProduction,
)
from zen_europe.elements.conversion_technologies.H2_DRI import H2_DRI
from zen_europe.elements.conversion_technologies.haber_bosch import HaberBosch
from zen_europe.elements.conversion_technologies.heat_industry_temp_conversion_100 import (  # noqa: E501
    HeatIndustryTempConversion100,
)
from zen_europe.elements.conversion_technologies.heat_industry_temp_conversion_150 import (  # noqa: E501
    HeatIndustryTempConversion150,
)
from zen_europe.elements.conversion_technologies.heat_industry_temp_conversion_rwh import (  # noqa: E501
    HeatIndustryTempConversionRWH,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry_0_100_waste_heat import (  # noqa: E501
    HeatPumpIndustry0100WasteHeat,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry_0_100_water import (  # noqa: E501
    HeatPumpIndustry0100Water,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry_100_150_waste_heat import (  # noqa: E501
    HeatPumpIndustry100150WasteHeat,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry_100_150_water import (  # noqa: E501
    HeatPumpIndustry100150Water,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry_150_200_waste_heat import (  # noqa: E501
    HeatPumpIndustry150200WasteHeat,
)
from zen_europe.elements.conversion_technologies.heat_pump_industry_150_200_water import (  # noqa: E501
    HeatPumpIndustry150200Water,
)
from zen_europe.elements.conversion_technologies.methanol_from_biomass import (
    MethanolFromBiomass,
)
from zen_europe.elements.conversion_technologies.methanol_from_hydrogen import (
    MethanolFromHydrogen,
)
from zen_europe.elements.conversion_technologies.natural_gas_boiler_industry import (
    NaturalGasBoilerIndustry,
)
from zen_europe.elements.conversion_technologies.NG_DRI import NG_DRI
from zen_europe.elements.conversion_technologies.oil_boiler_industry import (
    OilBoilerIndustry,
)
from zen_europe.elements.conversion_technologies.paper_production import (
    PaperProduction,
)
from zen_europe.elements.conversion_technologies.pyrolysis import Pyrolysis
from zen_europe.elements.conversion_technologies.waste_boiler_industry import (
    WasteBoilerIndustry,
)
from zen_europe.elements.conversion_technologies.waste_heat_integration_DH import (
    WasteHeatIntegrationDH,
)
from zen_europe.elements.retrofitting_technologies.cement_post_comb import (
    CementPostComb,
)
from zen_europe.elements.retrofitting_technologies.ceramic_post_comb import (
    CeramicPostComb,
)
from zen_europe.elements.retrofitting_technologies.glass_post_comb import (
    GlassPostComb,
)
from zen_europe.elements.retrofitting_technologies.hydrogen_to_ceramic_fuel import (
    HydrogenToCeramicFuel,
)
from zen_europe.elements.retrofitting_technologies.hydrogen_to_glass_fuel import (
    HydrogenToGlassFuel,
)
from zen_europe.elements.retrofitting_technologies.natural_gas_to_ceramic_fuel import (
    NaturalGasToCeramicFuel,
)
from zen_europe.elements.retrofitting_technologies.natural_gas_to_glass_fuel import (
    NaturalGasToGlassFuel,
)


class IndustrialHeatSector(Sector):
    """Industrial heat below 200 °C and recoverable waste heat: one heat carrier per
    temperature band, the boilers, heat pumps and the temperature cascade, shared by
    the glass, ceramic, paper and food sectors, and every technology of other sectors
    that consumes or produces these carriers."""

    name = "industrial_heat"
    required_sectors = [
        "electricity",
        "gas",
        "district_heating",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            HeatIndustry0100,
            HeatIndustry100150,
            HeatIndustry150200,
            RecoverableWasteHeat,
            # heat supply
            HeatPumpIndustry0100WasteHeat,
            HeatPumpIndustry0100Water,
            HeatPumpIndustry100150WasteHeat,
            HeatPumpIndustry100150Water,
            HeatPumpIndustry150200WasteHeat,
            HeatPumpIndustry150200Water,
            BiomassBoilerIndustry,
            ElectrodeBoilerIndustry,
            NaturalGasBoilerIndustry,
            OilBoilerIndustry,
            CoalBoilerIndustry,
            WasteBoilerIndustry,
            # temperature cascade
            HeatIndustryTempConversion150,
            HeatIndustryTempConversion100,
            HeatIndustryTempConversionRWH,
            # technologies of other sectors that consume or produce the carriers
            GlassProduction,
            CeramicProduction,
            PaperProduction,
            FoodProduction,
            Electrolysis,
            Gasification,
            AnaerobicDigestion,
            BiomethaneConversion,
            FischerTropsch,
            HaberBosch,
            MethanolFromBiomass,
            MethanolFromHydrogen,
            Pyrolysis,
            DAC,
            CementPostComb,
            GlassPostComb,
            CeramicPostComb,
            WasteHeatIntegrationDH,
            # industrial processes with recoverable waste heat
            NaturalGasToGlassFuel,
            HydrogenToGlassFuel,
            NaturalGasToCeramicFuel,
            HydrogenToCeramicFuel,
            CementProduction,
            BF_BOF,
            NG_DRI,
            H2_DRI,
            EAF,
        ]
