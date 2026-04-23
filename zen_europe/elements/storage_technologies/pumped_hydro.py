from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.elements import StorageTechnology
from zen_creator.utils.attribute import Attribute, SourceInformation


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
        attr = self.lifetime
    
        return attr.set_data(default_value=25, source=SourceInformation(
    description="Assumption for default pumped hydro lifetime.",
    metadata=MetaData(
        name="assumption",
        title="Modeling assumption",
        author=["ZEN Europe"],
        publication="ZEN Europe",
        publication_year=2026,
        url=None,
    ),
))
