from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.dea_energy_storage import DEAEnergyStorage

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import StorageTechnology
from zen_creator.utils.attribute import Attribute


class SaltCavernStorage(StorageTechnology):
    """Class containing all data and assumptions for hydrogen salt cavern
    storage technology."""

    name: str = "salt_cavern_storage"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of salt cavern storage to hydrogen.
        """
        return Attribute(
            name="reference_carrier", default_value=["hydrogen"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of salt cavern storage.
        """
        energy_storage = DEAEnergyStorage(source_path=self.source_path)
        return energy_storage.get_lifetime(self)

    def _set_capex_specific_storage(self) -> Attribute:
        """
        Sets the specific capex of the power capacity of salt cavern storage.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_storage(self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        """
        Sets the specific capex of the energy capacity of salt cavern storage.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_storage_energy(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed opex of salt cavern storage.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_efficiency_charge(self) -> Attribute:
        """
        Sets the charging efficiency of salt cavern storage.
        """
        energy_storage = DEAEnergyStorage(source_path=self.source_path)
        return energy_storage.get_efficiency_charge(self)

    def _set_efficiency_discharge(self) -> Attribute:
        """
        Sets the discharging efficiency of salt cavern storage.
        """
        energy_storage = DEAEnergyStorage(source_path=self.source_path)
        return energy_storage.get_efficiency_discharge(self)
