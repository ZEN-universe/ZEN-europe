from typing import ClassVar, Literal

from zen_creator.utils.settings import SettingsCategory

# Pathways of the cumulative global DAC capacity that the Sievert et al. (2024)
# experience curves are evaluated along, see `DACCostsSievert`.
DACDeploymentPathway = Literal[
    "IEA NZE 2050",
    "LNG analogue",
    "ammonia analogue",
    "ammonia + policy",
    "wind + policy",
]
DACTechnology = Literal["solid_sorbent", "liquid_solvent", "cao_weathering"]


class CostSettings(SettingsCategory):
    """Cost-related settings."""

    name: ClassVar[str] = "cost"

    use_learning_curves: bool = True
    use_nodal_biomass_prices: bool = False
    assume_oil_price_for_diesel_and_gasoline: bool = False

    # cost of DAC: the experience curves of Sievert et al. (2024) along a global
    # deployment pathway, or the technology cost database (DEA)
    dac_cost_source: Literal["tech_db", "sievert"] = "sievert"
    dac_technology: DACTechnology = "solid_sorbent"
    dac_deployment_pathway: DACDeploymentPathway = "IEA NZE 2050"
