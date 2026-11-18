# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import StorageTechnology
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.technology.dsm_literature_review import (
    DSMLiteratureReview,
)
from zen_europe.datasets.datasets.technology.industry_general_assumptions import (
    IndustryGeneralAssumptions,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class IndustryDSM:
    """Demand-side management: shifting the production of an industrial product."""

    carrier: ClassVar[str]

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Shifted product."""
        return Attribute(
            "reference_carrier", default_value=[self.carrier], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """No physical asset."""
        return self._assumptions().get_attribute(self, "lifetime", "dsm_lifetime")

    def _set_efficiency_charge(self) -> Attribute:
        """Small loss against simultaneous charging and discharging."""
        return self._assumptions().get_attribute(
            self, "efficiency_charge", "dsm_efficiency"
        )

    def _set_efficiency_discharge(self) -> Attribute:
        """Small loss against simultaneous charging and discharging."""
        return self._assumptions().get_attribute(
            self, "efficiency_discharge", "dsm_efficiency"
        )

    def _set_capex_specific_storage_energy(self) -> Attribute:
        """Cost of the product's demand-shiftability category."""
        return DSMLiteratureReview(self.source_path).get_capex_specific_storage_energy(
            self
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """Cost of the product's demand-shiftability category."""
        return DSMLiteratureReview(self.source_path).get_opex_specific_variable(self)

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        """Shifting horizon of the product's demand-shiftability category."""
        return DSMLiteratureReview(self.source_path).get_energy_to_power_ratio_max(self)

    def _set_capacity_limit(self) -> Attribute:
        """Stock limited to the product's demand, 0 at nodes without demand."""
        return DSMLiteratureReview(self.source_path).get_capacity_limit(self)

    def _assumptions(self) -> IndustryGeneralAssumptions:
        return IndustryGeneralAssumptions(self.source_path)


class GlassDSM(IndustryDSM, StorageTechnology):
    name: str = "glass_DSM"
    carrier: ClassVar[str] = "glass"


class CeramicDSM(IndustryDSM, StorageTechnology):
    name: str = "ceramic_DSM"
    carrier: ClassVar[str] = "ceramic"


class PaperDSM(IndustryDSM, StorageTechnology):
    name: str = "paper_DSM"
    carrier: ClassVar[str] = "paper"


class FoodDSM(IndustryDSM, StorageTechnology):
    name: str = "food_DSM"
    carrier: ClassVar[str] = "food"


class AmmoniaDSM(IndustryDSM, StorageTechnology):
    name: str = "ammonia_DSM"
    carrier: ClassVar[str] = "ammonia"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)


class ClinkerDSM(IndustryDSM, StorageTechnology):
    name: str = "clinker_DSM"
    carrier: ClassVar[str] = "clinker"


class MethanolDSM(IndustryDSM, StorageTechnology):
    name: str = "methanol_DSM"
    carrier: ClassVar[str] = "methanol"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)


class PrimarySteelDSM(IndustryDSM, StorageTechnology):
    name: str = "primary_steel_DSM"
    carrier: ClassVar[str] = "primary_steel"


class SecondarySteelDSM(IndustryDSM, StorageTechnology):
    name: str = "secondary_steel_DSM"
    carrier: ClassVar[str] = "secondary_steel"


class OlefinDSM(IndustryDSM, StorageTechnology):
    name: str = "olefin_DSM"
    carrier: ClassVar[str] = "olefin"
