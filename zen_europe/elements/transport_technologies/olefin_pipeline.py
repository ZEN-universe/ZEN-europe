from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.edges import Edges
from zen_europe.datasets.dataset_collections.transport_technologies_costs import (
    TransportTechnologiesCosts,
)
from zen_europe.datasets.datasets.technology.ammonia_pipelines_galimova import (
    AmmoniaPipelinesGalimova,
)
from zen_europe.datasets.datasets.technology.dea_energy_transport import (
    DEAEnergyTransport,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import TransportTechnology
from zen_creator.utils.attribute import Attribute


class OlefinPipeline(TransportTechnology):
    """Class containing all data and assumptions for olefin pipeline transport
    technology.

    All data is taken from the ammonia pipeline, as no data is available for
    olefin pipelines.
    """

    name: str = "olefin_pipeline"

    # the technology whose data is used for the olefin pipeline
    PROXY_TECHNOLOGY = "ammonia_pipeline"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of olefin pipeline to olefin.
        """
        return Attribute(
            name="reference_carrier", default_value=["olefin"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of olefin pipeline.
        """
        ammonia_pipelines = AmmoniaPipelinesGalimova(source_path=self.source_path)
        return ammonia_pipelines.get_lifetime(
            self, proxy_element_name=self.PROXY_TECHNOLOGY
        )

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of olefin pipeline.
        """
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        dea_energy_transport = DEAEnergyTransport(
            source_path=self.source_path,
        )
        return dea_energy_transport.get_construction_time(
            self, proxy_element_name="natural_gas_pipeline"
        )

    def _set_transport_loss_factor_linear(self) -> Attribute:
        """
        Sets the linear transport loss factor of olefin pipeline.
        """
        ammonia_pipelines = AmmoniaPipelinesGalimova(source_path=self.source_path)
        return ammonia_pipelines.get_transport_loss_factor_linear(
            self, proxy_element_name=self.PROXY_TECHNOLOGY
        )

    def _set_capex_per_distance_transport(self) -> Attribute:
        """
        Sets the distance-specific capex of olefin pipeline.

        The capex of the ammonia pipeline is rebased from the transported power
        onto the transported mass of product.
        """
        transport_costs = TransportTechnologiesCosts(
            settings=self.settings,
            source_path=self.source_path,
            set_nodes=self.model.config.system.set_nodes,
        )
        return transport_costs.get_capex_per_distance_transport(
            self, proxy_element_name=self.PROXY_TECHNOLOGY
        )

    # TODO implement opex_specific_fixed_per_distance in ZEN-garden
    # def _set_opex_specific_fixed(self) -> Attribute:
    #     """
    #     Sets the distance-specific fixed opex of olefin pipeline.
    #
    #     The fixed opex of the ammonia pipeline is rebased from the transported
    #     power onto the transported mass of product.
    #     """
    #     transport_costs = TransportTechnologiesCosts(
    #         settings=self.settings,
    #         source_path=self.source_path,
    #         set_nodes=self.model.config.system.set_nodes,
    #     )
    #     return transport_costs.get_opex_specific_fixed_per_distance(
    #         self, proxy_element_name=self.PROXY_TECHNOLOGY)

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit of olefin pipeline.

        Unless offshore chemical pipelines are allowed, the capacity limit is 0
        on the edges that cross the sea.
        """
        if self.settings.investment.allow_offshore_chemical_pipelines:
            return self.capacity_limit
        edges = Edges(source_path=self.source_path)
        return edges.get_capacity_limit_offshore(self)
