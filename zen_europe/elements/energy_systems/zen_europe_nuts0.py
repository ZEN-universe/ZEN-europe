from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.carbon_constraints import CarbonConstraints

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np
from zen_creator import AssumptionInformation, Attribute, EnergySystem, Scenario

from zen_europe.datasets.dataset_collections.edges import Edges
from zen_europe.datasets.datasets.energy_system.nuts_shp import NUTSshp
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)


class EnergySystemNuts0(EnergySystem):
    """Nuts0 energy system for Europe, with nodes based on NUTS0 regions
    and edges based on adjacency of NUTS regions and TYNDP data.
    """

    name: str = "energy_system_nuts0"

    # penalty price for emitting more than the carbon budget or the annual
    # limit allow
    PRICE_CARBON_EMISSIONS_OVERSHOOT = 5000

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
        attr.set_data(
            df=set_edges.drop_duplicates().sort_index(),
            source=AssumptionInformation(
                description=(
                    "The connections NO-BE and NO-FR for gas, and SE-LT for "
                    "electricity, are added manually."
                ),
            ),
        )

        # write csv
        return attr

    def _set_knowledge_depreciation_rate(self) -> Attribute:
        """
        Sets the knowledge depreciation rate of the energy system.
        """
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_knowledge_depreciation_rate(self)

    def _set_knowledge_spillover_rate(self) -> Attribute:
        """
        Sets the knowledge spillover rate between the nodes.
        """
        attr = self.knowledge_spillover_rate
        if self.settings.investment.use_inf_spillover_rate:
            return attr.set_data(
                default_value=np.inf,
                unit="1",
                source=AssumptionInformation(
                    description=(
                        "The knowledge spillover rate between the nodes is "
                        "infinite, so that knowledge is shared without any "
                        "loss between the nodes."
                    ),
                ),
            )
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_knowledge_spillover_rate(self)

    def _set_market_share_unbounded(self) -> Attribute:
        """
        Sets the market share that is exempt from the diffusion limit.
        """
        attr = self.market_share_unbounded
        if not self.settings.investment.use_unbounded_market_share:
            return attr.set_data(
                default_value=0,
                unit="1",
                source=AssumptionInformation(
                    description=("No market share is exempt from the diffusion limit."),
                ),
            )
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_market_share_unbounded(self)

    def _set_price_carbon_emissions_budget_overshoot(self) -> Attribute:
        """
        Sets the penalty price for overshooting the carbon budget.
        """
        attr = self.price_carbon_emissions_budget_overshoot
        return attr.set_data(
            default_value=self.PRICE_CARBON_EMISSIONS_OVERSHOOT,
            unit="Euro/tons",
            source=AssumptionInformation(
                description=(
                    f"The penalty price for overshooting the carbon budget is "
                    f"manually set to "
                    f"{self.PRICE_CARBON_EMISSIONS_OVERSHOOT} Euro per ton, "
                    f"far above any abatement cost, so that the budget is only "
                    f"overshot if the model would be infeasible otherwise."
                ),
            ),
        )

    def _set_price_carbon_emissions_annual_overshoot(self) -> Attribute:
        """
        Sets the penalty price for overshooting the annual carbon limit.

        The annual limit can only be overshot if it is an emission trading cap
        or if overshooting is allowed explicitly.
        """
        attr = self.price_carbon_emissions_annual_overshoot
        if not (
            self.settings.emissions.use_EU_ETS_cap
            or self.settings.emissions.use_annual_limit_overshoot
        ):
            return attr.set_data(
                default_value=np.inf,
                unit="Euro/tons",
                source=AssumptionInformation(
                    description=(
                        "The annual carbon emissions limit cannot be overshot."
                    ),
                ),
            )
        return attr.set_data(
            default_value=self.PRICE_CARBON_EMISSIONS_OVERSHOOT,
            unit="Euro/tons",
            source=AssumptionInformation(
                description=(
                    f"The penalty price for overshooting the annual carbon "
                    f"emissions limit is manually set to "
                    f"{self.PRICE_CARBON_EMISSIONS_OVERSHOOT} Euro per ton, "
                    f"far above any abatement cost, so that the limit is only "
                    f"overshot if the model would be infeasible otherwise."
                ),
            ),
        )

    def _set_discount_rate(self) -> Attribute:
        """
        Sets the discount rate of the energy system.
        """
        attr = self.discount_rate
        scenarios = None
        if self.settings.scenario.sensitivity_discount_rate:
            scenarios = Scenario("discount_rate", default_op=[0.0, 0.5, 1.5])
        return attr.set_data(
            default_value=0.05,
            unit="1",
            source=AssumptionInformation(
                description=("The discount rate is set to 0.05."),
            ),
            scenarios=scenarios,
        )

    def _set_carbon_emissions_budget(self) -> Attribute:
        """
        Sets the remaining carbon budget of the energy system.
        """
        attr = self.carbon_emissions_budget
        if not self.settings.emissions.use_carbon_budget:
            return attr.set_data(
                default_value=np.inf,
                unit="gigatons",
                source=AssumptionInformation(
                    description=(
                        "The remaining carbon budget is infinite, because the "
                        "carbon budget is not used in the model."
                    ),
                ),
            )
        carbon_constraints = CarbonConstraints(
            settings=self.settings, source_path=self.source_path
        )
        return carbon_constraints.calculate_carbon_budget(self)

    def _set_carbon_emissions_annual_limit(self) -> Attribute:
        """
        Sets the annual carbon emissions limit of the energy system.
        """
        attr = self.carbon_emissions_annual_limit
        if not self.settings.emissions.use_carbon_annual_limit:
            return attr.set_data(
                default_value=np.inf,
                unit="gigatons",
                source=AssumptionInformation(
                    description=(
                        "The annual carbon emissions limit is infinite, "
                        "because the annual limit is not used in the model."
                    ),
                ),
            )
        carbon_constraints = CarbonConstraints(
            settings=self.settings, source_path=self.source_path
        )
        return carbon_constraints.calculate_carbon_emissions_annual_limit(self)
