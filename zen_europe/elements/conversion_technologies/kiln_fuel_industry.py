# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.technology.cement_production_gardarsdottir import (
    CementProductionGardarsdottir,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)
from zen_europe.utils.industry import kiln_fuel

if TYPE_CHECKING:
    from zen_creator.model import Model


class KilnFuelIndustry:
    """Supply of a glass or ceramic kiln with natural gas, hydrogen or electricity.

    Without capex: only the choice of the fuel is modeled (AIDRES capex difference
    to the natural gas route ~0, see docs).
    """

    sector: ClassVar[str]
    fuel: ClassVar[str]
    # cement fuel technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str] = "hydrogen_to_cement_fuel"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Kiln fuel of the sector."""
        return Attribute(
            "reference_carrier", default_value=[self._kiln_fuel()], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Natural gas, hydrogen or electricity."""
        return Attribute("input_carrier", default_value=[self.fuel], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Kiln fuel of the sector."""
        return Attribute(
            "output_carrier", default_value=[self._kiln_fuel()], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Route efficiency from AIDRES."""
        return Aidres(self.source_path).get_conversion_factor_kiln_fuel(self)

    def _set_lifetime(self) -> Attribute:
        """
        Lifetime of the cement kiln, as the cement fuel technologies.

        The fuel supply is tied to the operation of the kiln.
        """
        gardarsdottir = CementProductionGardarsdottir(source_path=self.source_path)
        return gardarsdottir.get_lifetime(self).set_data(
            source=SourceInformation(
                description=(
                    "The lifetime of the kiln fuel technologies is the lifetime of "
                    "the cement kiln (Gardarsdottir et al. (2019)), as for the cement "
                    "fuel technologies, since the fuel supply is tied to the "
                    "operation of the kiln."
                ),
                metadata=gardarsdottir.metadata,
            ),
        )

    def _set_capacity_existing(self) -> Attribute:
        """Today's kiln natural gas demand."""
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
        ).get_capacity_existing_kiln_fuel(self)

    def _set_capacity_limit(self) -> Attribute:
        """Kiln fuel demand times the capacity limit margin, natural gas only."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_limit_kiln_fuel(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of the alternative kiln fuels; none for natural gas."""
        if (
            self.fuel == "natural_gas"
            or not self.settings.investment.use_diffusion_rates
        ):
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(
            self, proxy_element_name=self.diffusion_proxy
        )

    def _kiln_fuel(self) -> str:
        return kiln_fuel(self.sector)


class NaturalGasToKilnFuel(KilnFuelIndustry):
    fuel: ClassVar[str] = "natural_gas"


class HydrogenToKilnFuel(KilnFuelIndustry):
    fuel: ClassVar[str] = "hydrogen"


class ElectricityToKilnFuel(KilnFuelIndustry):
    fuel: ClassVar[str] = "electricity"


class NaturalGasToKilnFuelGlass(NaturalGasToKilnFuel, ConversionTechnology):
    name: str = "natural_gas_to_kiln_fuel_glass"
    sector: ClassVar[str] = "glass"


class NaturalGasToKilnFuelCeramic(NaturalGasToKilnFuel, ConversionTechnology):
    name: str = "natural_gas_to_kiln_fuel_ceramic"
    sector: ClassVar[str] = "ceramic"


class HydrogenToKilnFuelGlass(HydrogenToKilnFuel, ConversionTechnology):
    name: str = "hydrogen_to_kiln_fuel_glass"
    sector: ClassVar[str] = "glass"


class HydrogenToKilnFuelCeramic(HydrogenToKilnFuel, ConversionTechnology):
    name: str = "hydrogen_to_kiln_fuel_ceramic"
    sector: ClassVar[str] = "ceramic"


class ElectricityToKilnFuelGlass(ElectricityToKilnFuel, ConversionTechnology):
    name: str = "electricity_to_kiln_fuel_glass"
    sector: ClassVar[str] = "glass"


class ElectricityToKilnFuelCeramic(ElectricityToKilnFuel, ConversionTechnology):
    name: str = "electricity_to_kiln_fuel_ceramic"
    sector: ClassVar[str] = "ceramic"
