from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model


from zen_creator.elements import Carrier


class Heat(Carrier):

    name: str = "heat"

    def __init__(self, model: Model):
        super().__init__(model=model)

    # def _set_demand(self) -> Attribute:
    #     attr = super().demand
    #     demand_data = DatasetCollectionHeat(self.model.source_path).get_demand()
    #     return attr.set_data(
    #         df=demand_data,
    #         unit="GW",
    #         source="EU Building Observatory and When2Heat Dataset",
    #     )
