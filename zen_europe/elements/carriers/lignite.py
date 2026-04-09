from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model


from zen_creator.elements import Carrier


class Lignite(Carrier):

    name = "lignite"

    def __init__(self, model: Model):
        super().__init__(model=model)

    # def _set_carbon_intensity_carrier_import(self) -> Attribute:
    #     # TODO clean up
    #     attr = super().carbon_intensity_carrier_import
    #     return attr.set_data(default_value=0.400, source="Brown 2018")
