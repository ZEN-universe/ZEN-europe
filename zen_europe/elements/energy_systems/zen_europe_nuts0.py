from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, EnergySystem

from zen_europe.datasets.dataset_collections.edges import Edges
from zen_europe.datasets.datasets.energy_system.nuts_shp import NUTSshp


class EnergySystemNuts0(EnergySystem):
    """Nuts0 energy system for Europe, with nodes based on NUTS0 regions
    and edges based on adjacency of NUTS regions and TYNDP data.
    """

    name: str = "energy_system_nuts0"

    def __init__(self, model: Model):
        super().__init__(model=model)

    def _set_set_nodes(self) -> Attribute:
        attr = NUTSshp(source_path=self.source_path).get_set_nodes(self)
        return attr

    def _set_set_edges(self) -> Attribute:
        attr = Edges(source_path=self.source_path).get_set_edges(self)

        # check that edges are not empty
        if (set_edges := attr.df) is None or set_edges.empty:
            raise ValueError("No edges are set in the energy system.")

        # manual connections NO-BE and NO-FR for gas, and SE-LT for electricity
        set_edges.loc["NO-FR", :] = ["NO", "FR"]
        set_edges.loc["FR-NO", :] = ["FR", "NO"]
        set_edges.loc["NO-BE", :] = ["NO", "BE"]
        set_edges.loc["BE-NO", :] = ["BE", "NO"]
        set_edges.loc["SE-LT", :] = ["SE", "LT"]
        set_edges.loc["LT-SE", :] = ["LT", "SE"]
        attr.set_data(df=set_edges.drop_duplicates().sort_index())

        # write csv
        return attr
