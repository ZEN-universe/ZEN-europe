"""Cost of direct air capture along a global deployment pathway."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd
from zen_creator import Attribute, DatasetCollection, SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.technology.DAC_capacities_zurbriggen import (
    DACCapacitiesZurbriggen,
)
from zen_europe.datasets.datasets.technology.DAC_costs_sievert import (
    DACCostsSievert,
)
from zen_europe.datasets.datasets.technology.iea_net_zero_roadmap import (
    IEANetZeroRoadmap,
)
from zen_europe.settings.cost import DACDeploymentPathway

if TYPE_CHECKING:
    from zen_creator import ConversionTechnology, Dataset, Technology


class DACCosts(DatasetCollection):
    """
    Cost of DAC from the experience curves of Sievert et al. (2024), evaluated
    along a pathway of the cumulative global DAC capacity.

    The experience curves give the cost against the cumulative global capacity.
    The pathway (`cost.dac_deployment_pathway`) gives the capacity of each year,
    from the IEA Net Zero Roadmap or from the diffusion model of Zurbriggen et
    al. (2026). It is the capacity deployed worldwide, not the European capacity
    that ZEN-garden optimizes, and it does not depend on the investment decisions
    of the optimization (exogenous learning).
    """

    name = "dac_costs"

    IEA_PATHWAY = "IEA NZE 2050"

    DESCRIPTIONS = {
        "capex": "specific investment cost (total overnight cost)",
        "fopex": "fixed operational cost",
        "vopex": (
            "variable operational cost without electricity, heat, CO2 transport "
            "and CO2 storage"
        ),
    }

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any]]:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "sievert": DACCostsSievert(source_path=self.source_path),
            "iea": IEANetZeroRoadmap(source_path=self.source_path),
            "zurbriggen": DACCapacitiesZurbriggen(
                settings=self.settings, source_path=self.source_path
            ),
        }

    # -------- outward-facing accessors ------------------
    def get_capex_specific_conversion(self, element: ConversionTechnology) -> Attribute:
        """Specific investment cost of DAC along the global deployment pathway."""
        return self._set_cost_attribute(
            element, element.capex_specific_conversion, "capex", annual_values=True
        )

    def get_opex_specific_fixed(self, element: Technology) -> Attribute:
        """Fixed operational cost of DAC along the global deployment pathway."""
        return self._set_cost_attribute(
            element, element.opex_specific_fixed, "fopex", annual_values=True
        )

    def get_opex_specific_variable(self, element: Technology) -> Attribute:
        """Variable operational cost of DAC along the global deployment pathway."""
        return self._set_cost_attribute(
            element, element.opex_specific_variable, "vopex", annual_values=False
        )

    def get_global_capacity(
        self, pathway: DACDeploymentPathway, years: Sequence[int]
    ) -> pd.Series:
        """
        Cumulative global DAC capacity [tCO2/yr] of `pathway` in `years`.

        Every pathway starts from the cumulative capacity of the operational
        projects in the database of Zurbriggen et al. (2026), followed by the
        anchors of the pathway. The capacity grows at a constant rate between the
        anchor years, i.e. it is interpolated linearly in log space, and is
        constant outside of them.
        """
        operational = self._zurbriggen.get_global_dac_capacity_operational()
        anchors = self._pathway(pathway)
        anchors = pd.concat(
            [operational[operational.index < anchors.index.min()], anchors]
        )
        capacity = np.exp(
            np.interp(
                np.asarray(years, dtype=float),
                anchors.index.to_numpy(dtype=float),
                np.log(anchors.to_numpy(dtype=float)),
            )
        )
        return pd.Series(capacity, index=pd.Index(years, name="year"))

    # -------- helpers ------------------
    def _pathway(self, pathway: DACDeploymentPathway) -> pd.Series:
        """The anchors of `pathway` from the source that reports it."""
        if pathway == self.IEA_PATHWAY:
            return self._iea.get_global_dac_capacity()
        return self._zurbriggen.get_global_dac_capacity(pathway)

    def _pathway_source(self, pathway: DACDeploymentPathway) -> str:
        if pathway == self.IEA_PATHWAY:
            return "the IEA Net Zero Roadmap (2023), Net Zero Emissions scenario"
        return f"Zurbriggen et al. (2026), '{pathway}'"

    @property
    def _sievert(self) -> DACCostsSievert:
        return cast(DACCostsSievert, self.data["sievert"])

    @property
    def _iea(self) -> IEANetZeroRoadmap:
        return cast(IEANetZeroRoadmap, self.data["iea"])

    @property
    def _zurbriggen(self) -> DACCapacitiesZurbriggen:
        return cast(DACCapacitiesZurbriggen, self.data["zurbriggen"])

    def _set_cost_attribute(
        self,
        element: Technology,
        attribute: Attribute,
        variable: str,
        annual_values: bool,
    ) -> Attribute:
        """
        Set `attribute` to the cost of `variable` in the years of the model.

        Like `TechnologyCostDatabase`, the capex and the fixed opex are given per
        year (`annual_values`), the variable opex as the value of the reference
        year and its yearly variation. Without learning curves the cost of the
        reference year is used in all years.

        The settings are read from `element`, since the collection is a
        singleton that keeps the settings of its first call.
        """
        settings = element.settings
        reference_year = settings.time.reference_year
        technology = settings.cost.dac_technology
        pathway = settings.cost.dac_deployment_pathway
        capacity = self.get_global_capacity(pathway, settings.time.years)
        cost = pd.Series(
            self._sievert.get_cost(
                technology, variable, capacity.to_numpy(), reference_year
            ),
            index=capacity.index,
        )
        default_value = float(cost.loc[reference_year])

        df: pd.Series | None = None
        yearly_variations: pd.Series | None = None
        if settings.cost.use_learning_curves:
            if annual_values:
                df = cost if cost.nunique() > 1 else None
            else:
                if default_value <= 0:
                    raise ValueError(
                        f"The {variable} of DAC ({technology}) is not positive in "
                        f"{reference_year}, so its yearly variation is undefined."
                    )
                yearly_variations = cost / default_value
        for frame in (df, yearly_variations):
            if frame is not None:
                frame.index.name = "year"
                frame.name = attribute.name

        source = SourceInformation(
            description=(
                f"{self.DESCRIPTIONS[variable].capitalize()} of '{element.name}' is "
                f"the median of the experience curve of the {technology} DAC "
                "technology of Sievert et al. (2024), evaluated at the cumulative "
                "global DAC capacity of the deployment pathway of "
                f"{self._pathway_source(pathway)}, starting from the operational "
                "projects in the DAC project database of Zurbriggen et al. (2026). "
                + (
                    ""
                    if settings.cost.use_learning_curves
                    else f"The cost of {reference_year} is used in all years. "
                )
                + f"Converted from US${DACCostsSievert.MONEY_YEAR} with the ECB "
                f"exchange rate and rebased to {reference_year} Euro with ECB HICP "
                "inflation."
            ),
            metadata=self.metadata,
        )
        return attribute.set_data(
            default_value=default_value,
            df=df,
            yearly_variations_df=yearly_variations,
            unit=self._sievert.get_unit(variable),
            source=source,
        )
