from __future__ import annotations

from turtle import pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import MetaData, StorageTechnologyConfig, StorageTechnology, Attribute, SourceInformation
from zen_europe.datasets.datasets import EntsoePPDataset, TYNDP2024Dataset

class PumpedHydroConfig(StorageTechnologyConfig):
    """
    Configuration class for the PumpedHydro.

    This class is used to define the configuration parameters for the
    PumpedHydro.

    """

    name: str = "pumped_hydro"

    use_entsoe_existing_capacities: bool = True

class PumpedHydro(StorageTechnology):
    """Class containing all data and assumptions for pumped hydro storage technology."""

    name: str = "pumped_hydro"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of pumped hydro to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Return the lifetime of pumped hydro.

        Currently returns the default value. This method can be
        customized to return a specific lifetime for pumped hydro,
        either as a constant value or as a time series if the lifetime
        varies over time.
        """
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        """
        Return the capacity existing of pumped hydro.

        Currently returns the default value. This method can be
        customized to return a specific capacity existing for pumped hydro,
        either as a constant value or as a time series if the capacity
        varies over time.
        """
        attr = self.capacity_existing
 
        if self.model.config.data.storage_techonology.pumped_hydro.use_ensoe_existing_capacities:
            attr = EntsoePPDataset(self.source_path).get_capacity(element=self)

        return attr
    
    def _set_capacity_existing_energy(self) -> Attribute:
            """Return the energy capacity existing of pumped hydro."""
            ep_ratio = 6.0  
            
            # Get power capacity to calculate energy capacity
            power_attr = self._set_capacity_existing()
                
            df_energy = pd.DataFrame({
                "capacity_existing_energy": power_attr.df["capacity_existing"] * ep_ratio
            })
                
            attr = self.capacity_existing_energy
            attr.set_data(
                df=df_energy,
                unit="GWh",
                source=power_attr.sources[0]
            )
            return attr
