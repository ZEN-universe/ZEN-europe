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

if TYPE_CHECKING:
    from zen_creator.model import Model


class NaturalGasToKilnFuelCeramic(ConversionTechnology):
    """Natural gas firing of the ceramic kilns.

    Without capex: only the choice of the fuel is modeled (AIDRES capex difference
    to the natural gas route ~0, see docs).
    """

    name: str = "natural_gas_to_kiln_fuel_ceramic"
    sector: ClassVar[str] = "ceramic"
    fuel: ClassVar[str] = "natural_gas"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Ceramic fuel."""
        return Attribute(
            "reference_carrier", default_value=["ceramic_fuel"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Natural gas."""
        return Attribute("input_carrier", default_value=["natural_gas"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Ceramic fuel."""
        return Attribute("output_carrier", default_value=["ceramic_fuel"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Reference route of AIDRES."""
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
        """Today's ceramic kiln natural gas demand."""
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
        """Ceramic fuel demand times the capacity limit margin."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_limit_kiln_fuel(self)
