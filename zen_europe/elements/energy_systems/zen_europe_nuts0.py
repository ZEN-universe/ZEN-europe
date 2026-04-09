from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.utils.attribute import Attribute

from .energy_system import EnergySystem


class TemplateEnergySystem(EnergySystem):
    """Template class for energy systems.

    This template is a starting point for implementing a custom energy system
    class. You must implement both methods below to provide `set_nodes` and
    `set_edges` for your model.

    Search for `TODO` markers to find sections that should be customized.
    """

    name: str = "template_energy_system"

    def __init__(self, model: Model):
        super().__init__(model=model)

    def _set_set_nodes(self) -> Attribute:
        """Return the set_nodes attribute.

        TODO: Replace this placeholder with your node-loading logic.
        """
        return Attribute(name="set_nodes", default_value=None, element=self)

    def _set_set_edges(self) -> Attribute:
        """Return the set_edges attribute.

        TODO: Replace this placeholder with your edge-loading logic.
        """
        return Attribute(name="set_edges", default_value=None, element=self)

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
