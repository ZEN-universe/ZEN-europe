# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import StorageTechnology
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.datasets.datasets.technology.brown2018 import Brown2018
from zen_europe.datasets.datasets.technology.industry_general_assumptions import (
    IndustryGeneralAssumptions,
)
from zen_europe.datasets.datasets.technology.mayer2024 import Mayer2024
from zen_europe.utils.industry import heat_carrier

if TYPE_CHECKING:
    from zen_creator.model import Model


class IndustryTES:
    """Thermal energy storage for one sector and temperature band."""

    sector: ClassVar[str]
    temp_level: ClassVar[str]
    storage_type: ClassVar[str]
    # Brown et al. (2018) technology for the self-discharge
    self_discharge_proxy: ClassVar[str] = "hot water tank central"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the sector's temperature band."""
        return Attribute(
            "reference_carrier",
            default_value=[heat_carrier(self.temp_level, self.sector)],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """Lifetime from Mayer et al. (2024)."""
        return Mayer2024(self.source_path).get_lifetime(self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        """Investment cost from Mayer et al. (2024)."""
        return Mayer2024(self.source_path).get_capex_specific_storage_energy(self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        """Fixed O&M cost from Mayer et al. (2024)."""
        return Mayer2024(self.source_path).get_opex_specific_fixed_energy(self)

    def _set_efficiency_charge(self) -> Attribute:
        """Losses neglected."""
        return self._assumptions().get_attribute(
            self, "efficiency_charge", "tes_efficiency"
        )

    def _set_efficiency_discharge(self) -> Attribute:
        """Losses neglected."""
        return self._assumptions().get_attribute(
            self, "efficiency_discharge", "tes_efficiency"
        )

    def _set_self_discharge(self) -> Attribute:
        """Self-discharge from Brown et al. (2018)."""
        return Brown2018(self.source_path).get_self_discharge(
            self, self.self_discharge_proxy
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """Small cost against cycling."""
        return self._assumptions().get_attribute(
            self, "opex_specific_variable", "tes_opex_variable"
        )

    def _set_capacity_limit(self) -> Attribute:
        """Heat demand of the band and all lower bands times the capacity limit
        margin."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_limit_tes(self)

    def _set_energy_to_power_ratio_min(self) -> Attribute:
        """Minimum duration of the storage type."""
        return self._assumptions().get_attribute(
            self,
            "energy_to_power_ratio_min",
            "tes_energy_to_power_ratio_min",
            self._storage_key(),
        )

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        """Maximum duration of the storage type."""
        return self._assumptions().get_attribute(
            self,
            "energy_to_power_ratio_max",
            "tes_energy_to_power_ratio_max",
            self._storage_key(),
        )

    def _storage_key(self) -> str:
        """Key of the storage type in the general industry assumptions."""
        return self.storage_type.replace(" ", "_")

    def _assumptions(self) -> IndustryGeneralAssumptions:
        return IndustryGeneralAssumptions(self.source_path)


class IndustryTESWater0100(IndustryTES):
    temp_level: ClassVar[str] = "0_100"
    storage_type: ClassVar[str] = "water tank"


class IndustryTESWater100150(IndustryTES):
    temp_level: ClassVar[str] = "100_150"
    storage_type: ClassVar[str] = "water tank"


class IndustryTESSteam150200(IndustryTES):
    temp_level: ClassVar[str] = "150_200"
    storage_type: ClassVar[str] = "steam accumulator"


class IndustryTESWater0100Glass(IndustryTESWater0100, StorageTechnology):
    name: str = "industry_TES_water_0_100_glass"
    sector: ClassVar[str] = "glass"


class IndustryTESWater0100Ceramic(IndustryTESWater0100, StorageTechnology):
    name: str = "industry_TES_water_0_100_ceramic"
    sector: ClassVar[str] = "ceramic"


class IndustryTESWater0100Paper(IndustryTESWater0100, StorageTechnology):
    name: str = "industry_TES_water_0_100_paper"
    sector: ClassVar[str] = "paper"


class IndustryTESWater0100Food(IndustryTESWater0100, StorageTechnology):
    name: str = "industry_TES_water_0_100_food"
    sector: ClassVar[str] = "food"


class IndustryTESWater100150Glass(IndustryTESWater100150, StorageTechnology):
    name: str = "industry_TES_water_100_150_glass"
    sector: ClassVar[str] = "glass"


class IndustryTESWater100150Ceramic(IndustryTESWater100150, StorageTechnology):
    name: str = "industry_TES_water_100_150_ceramic"
    sector: ClassVar[str] = "ceramic"


class IndustryTESWater100150Paper(IndustryTESWater100150, StorageTechnology):
    name: str = "industry_TES_water_100_150_paper"
    sector: ClassVar[str] = "paper"


class IndustryTESWater100150Food(IndustryTESWater100150, StorageTechnology):
    name: str = "industry_TES_water_100_150_food"
    sector: ClassVar[str] = "food"


class IndustryTESSteam150200Glass(IndustryTESSteam150200, StorageTechnology):
    name: str = "industry_TES_steam_150_200_glass"
    sector: ClassVar[str] = "glass"


class IndustryTESSteam150200Ceramic(IndustryTESSteam150200, StorageTechnology):
    name: str = "industry_TES_steam_150_200_ceramic"
    sector: ClassVar[str] = "ceramic"


class IndustryTESSteam150200Paper(IndustryTESSteam150200, StorageTechnology):
    name: str = "industry_TES_steam_150_200_paper"
    sector: ClassVar[str] = "paper"


class IndustryTESSteam150200Food(IndustryTESSteam150200, StorageTechnology):
    name: str = "industry_TES_steam_150_200_food"
    sector: ClassVar[str] = "food"
