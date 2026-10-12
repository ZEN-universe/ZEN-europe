from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.battery_storage_nrel import (
    BatteryStorageNREL,
)
from zen_europe.datasets.datasets.technology.emmes_energy_storage import (
    EMMESEnergyStorage,
)
from zen_europe.datasets.datasets.technology.self_discharge_alt import SelfDischargeAlt
from zen_europe.datasets.datasets.technology.storage_technologies_schmidt import (
    StorageTechnologiesSchmidt,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.elements import StorageTechnology
from zen_creator.utils.attribute import Attribute


class Battery(StorageTechnology):
    """Class containing all data and assumptions for battery storage technology."""

    name: str = "battery"
    ENTSOE_PSR = "B25"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of battery to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of battery.
        """
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of battery.
        """
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_construction_time(self)

    def _set_capex_specific_storage(self) -> Attribute:
        """
        Sets the specific capex of the power capacity of battery.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_storage(self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        """
        Sets the specific capex of the energy capacity of battery.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_storage_energy(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed opex of battery.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_efficiency_charge(self) -> Attribute:
        """
        Sets the charging efficiency of battery.
        """
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_efficiency_charge(self)

    def _set_efficiency_discharge(self) -> Attribute:
        """
        Sets the discharging efficiency of battery.
        """
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_efficiency_discharge(self)

    def _set_self_discharge(self) -> Attribute:
        """
        Sets the self-discharge of battery.
        """
        self_discharge_dataset = SelfDischargeAlt(source_path=self.source_path)
        return self_discharge_dataset.get_self_discharge(self)

    def _set_energy_to_power_ratio_min(self) -> Attribute:
        """
        Sets the minimum energy-to-power ratio of battery.
        """
        if not self.settings.investment.use_battery_e2p_ratio:
            return self.energy_to_power_ratio_min
        battery_storage = BatteryStorageNREL(source_path=self.source_path)
        return battery_storage.get_energy_to_power_ratio_min(self)

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        """
        Sets the maximum energy-to-power ratio of battery.
        """
        if not self.settings.investment.use_battery_e2p_ratio:
            return self.energy_to_power_ratio_max
        battery_storage = BatteryStorageNREL(source_path=self.source_path)
        return battery_storage.get_energy_to_power_ratio_max(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of battery.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of battery.
        """
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities.",
                ),
            )
        emmes = EMMESEnergyStorage(source_path=self.source_path)
        return emmes.get_capacity_existing(self)

    def _set_capacity_existing_energy(self) -> Attribute:
        """
        Sets the existing energy capacity of battery.
        """
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing_energy.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities.",
                ),
            )
        capacity_existing = self.capacity_existing.df
        battery_storage = BatteryStorageNREL(source_path=self.source_path)
        e2p_ratio = battery_storage._get_e2p_ratio(self)
        capacity_existing_energy = capacity_existing * e2p_ratio
        capacity_existing_energy.name = "capacity_existing_energy"
        return self.capacity_existing_energy.set_data(
            df=capacity_existing_energy,
            source=AssumptionInformation(
                description=(
                    "The existing energy capacity of battery is calculated by "
                    "multiplying the existing power capacity with the maximum "
                    "energy-to-power ratio."
                ),
            ),
        )
