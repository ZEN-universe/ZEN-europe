# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.elements.conversion_technologies.industry_heat_technology import (
    IndustryHeatTechnology,
)
from zen_europe.utils.industry import heat_carrier


class BoilerIndustry(IndustryHeatTechnology):
    """
    Industrial boiler of one sector, supplying the 150-200 °C band.

    The boilers exist for every combination of fuel and sector. The shared data and
    assumptions are defined once in this mixin and the fuel mixins below; the
    concrete technologies at the end of the module only set the sector.
    """

    fuel: ClassVar[str]
    input: ClassVar[str]

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the sector's 150-200 °C band."""
        return Attribute(
            "reference_carrier", default_value=[self._heat()], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Fuel of the boiler."""
        return Attribute("input_carrier", default_value=[self.input], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Heat of the sector's 150-200 °C band."""
        return Attribute("output_carrier", default_value=[self._heat()], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Inverse of the DEA efficiency."""
        tech_db = self._cost_db()
        efficiency, agencies = tech_db.get_efficiency(
            self, proxy_element_name=self.cost_proxy
        )
        efficiency = efficiency.loc[self.settings.time.reference_year]
        return self.conversion_factor.set_data(
            default_value=[
                {self.input: {"default_value": 1 / efficiency, "unit": "GW/GW"}}
            ],
            source=SourceInformation(
                description=(
                    f"Inverse of the efficiency of '{self.cost_proxy}' "
                    f"from {', '.join(agencies)}."
                ),
                metadata=tech_db.metadata,
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost from DEA."""
        return self._cost_db().get_capex_specific_conversion(
            self, proxy_element_name=self.cost_proxy
        )

    def _set_capacity_existing(self) -> Attribute:
        """Today's heat demand, split by fuel."""
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities."
                ),
            )
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_existing_boiler(self)

    def _heat(self) -> str:
        return heat_carrier("150_200", self.sector)


class BiomassBoilerIndustry(BoilerIndustry):
    fuel: ClassVar[str] = "biomass"
    input: ClassVar[str] = "biomass"
    cost_proxy: ClassVar[str] = "biomass_boiler_industry"
    diffusion_proxy: ClassVar[str] = "biomass_boiler_DH"


class ElectrodeBoilerIndustry(BoilerIndustry):
    fuel: ClassVar[str] = "electrode"
    input: ClassVar[str] = "electricity"
    cost_proxy: ClassVar[str] = "electrode_boiler_industry"
    diffusion_proxy: ClassVar[str] = "electrode_boiler_DH"


class NaturalGasBoilerIndustry(BoilerIndustry):
    fuel: ClassVar[str] = "natural_gas"
    input: ClassVar[str] = "natural_gas"
    cost_proxy: ClassVar[str] = "natural_gas_boiler_industry"
    diffusion_proxy: ClassVar[str] = "natural_gas_boiler_DH"


class OilBoilerIndustry(BoilerIndustry):
    fuel: ClassVar[str] = "oil"
    input: ClassVar[str] = "oil"
    cost_proxy: ClassVar[str] = "oil_boiler_industry"
    diffusion_proxy: ClassVar[str] = "oil_boiler_DH"


class CoalBoilerIndustry(BoilerIndustry):
    fuel: ClassVar[str] = "coal"
    input: ClassVar[str] = "hard_coal"
    cost_proxy: ClassVar[str] = "coal_boiler_industry"
    diffusion_proxy: ClassVar[str] = "hard_coal_boiler_DH"


class WasteBoilerIndustry(BoilerIndustry):
    """No DEA data: efficiency, lifetime and costs as the DH waste boiler."""

    fuel: ClassVar[str] = "waste"
    input: ClassVar[str] = "waste"
    diffusion_proxy: ClassVar[str] = "waste_boiler_DH"

    def _set_conversion_factor(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("conversion_factor")

    def _set_lifetime(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("lifetime")

    def _set_construction_time(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("construction_time")

    def _set_capex_specific_conversion(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("capex_specific_conversion")

    def _set_opex_specific_fixed(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("opex_specific_fixed")

    def _set_opex_specific_variable(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("opex_specific_variable")

    def _as_dh_boiler(self, name: str) -> Attribute:
        """Copy the attribute `name` of waste_boiler_DH."""
        dh_attribute = getattr(
            self.model.conversion_technologies["waste_boiler_DH"], name
        )
        return getattr(self, name).set_data(
            default_value=dh_attribute.default_value,
            unit=dh_attribute.unit,
            df=dh_attribute.df,
            yearly_variations_df=dh_attribute.yearly_variations_df,
            source=AssumptionInformation(description="As waste_boiler_DH."),
        )


class BiomassBoilerIndustryGlass(BiomassBoilerIndustry, ConversionTechnology):
    name: str = "biomass_boiler_industry_glass"
    sector: ClassVar[str] = "glass"


class BiomassBoilerIndustryCeramic(BiomassBoilerIndustry, ConversionTechnology):
    name: str = "biomass_boiler_industry_ceramic"
    sector: ClassVar[str] = "ceramic"


class BiomassBoilerIndustryPaper(BiomassBoilerIndustry, ConversionTechnology):
    name: str = "biomass_boiler_industry_paper"
    sector: ClassVar[str] = "paper"


class BiomassBoilerIndustryFood(BiomassBoilerIndustry, ConversionTechnology):
    name: str = "biomass_boiler_industry_food"
    sector: ClassVar[str] = "food"


class ElectrodeBoilerIndustryGlass(ElectrodeBoilerIndustry, ConversionTechnology):
    name: str = "electrode_boiler_industry_glass"
    sector: ClassVar[str] = "glass"


class ElectrodeBoilerIndustryCeramic(ElectrodeBoilerIndustry, ConversionTechnology):
    name: str = "electrode_boiler_industry_ceramic"
    sector: ClassVar[str] = "ceramic"


class ElectrodeBoilerIndustryPaper(ElectrodeBoilerIndustry, ConversionTechnology):
    name: str = "electrode_boiler_industry_paper"
    sector: ClassVar[str] = "paper"


class ElectrodeBoilerIndustryFood(ElectrodeBoilerIndustry, ConversionTechnology):
    name: str = "electrode_boiler_industry_food"
    sector: ClassVar[str] = "food"


class NaturalGasBoilerIndustryGlass(NaturalGasBoilerIndustry, ConversionTechnology):
    name: str = "natural_gas_boiler_industry_glass"
    sector: ClassVar[str] = "glass"


class NaturalGasBoilerIndustryCeramic(NaturalGasBoilerIndustry, ConversionTechnology):
    name: str = "natural_gas_boiler_industry_ceramic"
    sector: ClassVar[str] = "ceramic"


class NaturalGasBoilerIndustryPaper(NaturalGasBoilerIndustry, ConversionTechnology):
    name: str = "natural_gas_boiler_industry_paper"
    sector: ClassVar[str] = "paper"


class NaturalGasBoilerIndustryFood(NaturalGasBoilerIndustry, ConversionTechnology):
    name: str = "natural_gas_boiler_industry_food"
    sector: ClassVar[str] = "food"


class OilBoilerIndustryGlass(OilBoilerIndustry, ConversionTechnology):
    name: str = "oil_boiler_industry_glass"
    sector: ClassVar[str] = "glass"


class OilBoilerIndustryCeramic(OilBoilerIndustry, ConversionTechnology):
    name: str = "oil_boiler_industry_ceramic"
    sector: ClassVar[str] = "ceramic"


class OilBoilerIndustryPaper(OilBoilerIndustry, ConversionTechnology):
    name: str = "oil_boiler_industry_paper"
    sector: ClassVar[str] = "paper"


class OilBoilerIndustryFood(OilBoilerIndustry, ConversionTechnology):
    name: str = "oil_boiler_industry_food"
    sector: ClassVar[str] = "food"


class CoalBoilerIndustryGlass(CoalBoilerIndustry, ConversionTechnology):
    name: str = "coal_boiler_industry_glass"
    sector: ClassVar[str] = "glass"


class CoalBoilerIndustryCeramic(CoalBoilerIndustry, ConversionTechnology):
    name: str = "coal_boiler_industry_ceramic"
    sector: ClassVar[str] = "ceramic"


class CoalBoilerIndustryPaper(CoalBoilerIndustry, ConversionTechnology):
    name: str = "coal_boiler_industry_paper"
    sector: ClassVar[str] = "paper"


class CoalBoilerIndustryFood(CoalBoilerIndustry, ConversionTechnology):
    name: str = "coal_boiler_industry_food"
    sector: ClassVar[str] = "food"


class WasteBoilerIndustryGlass(WasteBoilerIndustry, ConversionTechnology):
    name: str = "waste_boiler_industry_glass"
    sector: ClassVar[str] = "glass"


class WasteBoilerIndustryCeramic(WasteBoilerIndustry, ConversionTechnology):
    name: str = "waste_boiler_industry_ceramic"
    sector: ClassVar[str] = "ceramic"


class WasteBoilerIndustryPaper(WasteBoilerIndustry, ConversionTechnology):
    name: str = "waste_boiler_industry_paper"
    sector: ClassVar[str] = "paper"


class WasteBoilerIndustryFood(WasteBoilerIndustry, ConversionTechnology):
    name: str = "waste_boiler_industry_food"
    sector: ClassVar[str] = "food"
