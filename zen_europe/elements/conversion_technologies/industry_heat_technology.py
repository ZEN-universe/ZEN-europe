from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class IndustryHeatTechnology:
    """
    Data shared by the industrial boilers, heat pumps and post-combustion capture:
    costs, lifetime and construction time of a DEA proxy, diffusion as a proxy
    technology.
    """

    sector: ClassVar[str]
    # DEA technology the costs, lifetime and construction time are taken from
    cost_proxy: ClassVar[str]
    # technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str]

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_lifetime(self) -> Attribute:
        """Lifetime from DEA."""
        return self._cost_db().get_lifetime(self, proxy_element_name=self.cost_proxy)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Fixed O&M cost from DEA."""
        return self._cost_db().get_opex_specific_fixed(
            self, proxy_element_name=self.cost_proxy
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """Variable O&M cost from DEA."""
        return self._cost_db().get_opex_specific_variable(
            self, proxy_element_name=self.cost_proxy
        )

    def _set_construction_time(self) -> Attribute:
        """Construction time from DEA."""
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        return self._cost_db().get_construction_time(
            self, proxy_element_name=self.cost_proxy
        )

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of the district heating proxy."""
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(
            self, proxy_element_name=self.diffusion_proxy
        )

    def _cost_db(self) -> TechnologyCostDatabase:
        return TechnologyCostDatabase(self.settings, self.source_path)
