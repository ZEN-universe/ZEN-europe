from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from zen_europe.datasets.dataset_collections.power_line_capacity_limit import (
    PowerLineCapacityLimit,
)
from zen_europe.datasets.dataset_collections.transport_technologies_costs import (
    TransportTechnologiesCosts,
)
from zen_europe.datasets.datasets.carrier.entsoe import ENTSOE
from zen_europe.datasets.datasets.technology.dea_energy_transport import (
    DEAEnergyTransport,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    SourceInformation,
    TransportTechnology,
)


class PowerLine(TransportTechnology):
    """Class containing all data and assumptions for power line transport technology."""

    name: str = "power_line"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of power line to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of power line.

        Returns the value of the existing model, which is the 60 years of the
        link technologies of Euro-Calliope.
        """
        energy_transport = DEAEnergyTransport(source_path=self.source_path)
        return energy_transport.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of power line.
        """
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        dea_energy_transport = DEAEnergyTransport(
            source_path=self.source_path,
        )
        return dea_energy_transport.get_construction_time(self)

    def _set_transport_loss_factor_linear(self) -> Attribute:
        """
        Sets the linear transport loss factor of power line.
        """
        energy_transport = DEAEnergyTransport(source_path=self.source_path)
        return energy_transport.get_transport_loss_factor_linear(self)

    def _set_capex_per_distance_transport(self) -> Attribute:
        """
        Sets the distance-specific capex of power line.

        TODO add offshore cost increase for power line
        """
        transport_costs = TransportTechnologiesCosts(
            settings=self.settings,
            source_path=self.source_path,
            set_nodes=self.model.config.system.set_nodes,
        )
        return transport_costs.get_capex_per_distance_transport(self)

    # TODO implement opex_specific_fixed_per_distance in ZEN-garden
    # def _set_opex_specific_fixed(self) -> Attribute:
    #     """
    #     Sets the distance-specific fixed opex of power line.
    #     """
    #     transport_costs = TransportTechnologiesCosts(
    #         settings=self.settings,
    #         source_path=self.source_path,
    #         set_nodes=self.model.config.system.set_nodes,
    #     )
    #     return transport_costs.get_opex_specific_fixed_per_distance(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of power line.

        The existing capacity is the net transfer capacity between
        neighbouring countries.
        """
        if not self.settings.investment.use_existing_capacities:
            attr = self.capacity_existing
            return attr.set_data(
                default_value=0,
                source=AssumptionInformation(
                    description="We do not consider existing capacities.",
                ),
            )
        entsoe = ENTSOE(
            settings=self.settings,
            set_nodes=self.model.config.system.set_nodes,
            source_path=self.source_path,
        )
        capacity_existing = entsoe.get_transmission_capacity()
        # the cached queries of the platform can cover more countries than the
        # model, so only the edges of the model are kept
        set_edges = self.model.energy_system.set_edges.df
        capacity_existing = capacity_existing[
            capacity_existing.index.get_level_values("edge").isin(set_edges.index)
        ]
        # DE-LU and LU-DE are not in the ENTSO-E Transparency Platform, as the
        # two countries share a bidding zone, so they get the highest value of
        # all edges
        max_capacity = capacity_existing["capacity_existing"].max()
        year = capacity_existing.index.get_level_values("year_construction").max()
        capacity_existing.loc[("DE-LU", year), "capacity_existing"] = max_capacity
        capacity_existing.loc[("LU-DE", year), "capacity_existing"] = max_capacity
        capacity_existing = capacity_existing.sort_index()
        attr = self.capacity_existing
        return attr.set_data(
            df=capacity_existing,
            unit="GW",
            source=SourceInformation(
                description=(
                    "The existing capacity of power lines is the net transfer "
                    "capacity between neighbouring countries of the ENTSO-E "
                    "Transparency Platform."
                ),
                metadata=entsoe.metadata,
            ),
        )

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit of power line.

        The capacity limit is the capacity that the European network can reach
        on an edge, so power lines can only be expanded on the edges that the
        network studies cover.
        """
        attr = self.capacity_limit
        if not self.settings.investment.use_power_line_capacity_limit:
            return attr.set_data(
                default_value=np.inf,
                source=AssumptionInformation(
                    description=("We do not limit the capacity of the power lines."),
                ),
            )
        capacity_limit = PowerLineCapacityLimit(
            settings=self.settings,
            source_path=self.source_path,
            set_nodes=self.model.config.system.set_nodes,
        )
        return capacity_limit.get_capacity_limit(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of power line.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
