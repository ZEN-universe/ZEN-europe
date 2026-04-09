from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import (
    TransportTechnology,
)
from zen_creator.utils.attribute import Attribute


class NaturalGasPipeline(TransportTechnology):

    name: str = "natural_gas_pipeline"

    def __init__(self, model: Model):
        super().__init__(model=model)

    def _set_lifetime(self) -> Attribute:
        attr = self._lifetime
        # return attr.set_data(default_value=50, source="assumption")
        return attr

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(
            name="reference_carrier", default_value=["natural_gas"], element=self
        )
