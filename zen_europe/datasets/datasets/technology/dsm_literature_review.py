from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import AssumptionInformation, MetaData
from zen_creator.utils.attribute import Attribute

from zen_europe.utils.constants import Constants
from zen_europe.utils.industry import model_nodes

if TYPE_CHECKING:
    from zen_europe.elements.storage_technologies.industry_DSM import IndustryDSM

# energy content (GWh/t) of the carriers modeled on an energy basis
ENERGY_CONTENT = {
    "ammonia": Constants.AMMONIA_GWH_PER_TON,
    "methanol": Constants.METHANOL_KWH_PER_KG / 1000,  # kWh/kg -> GWh/t
}


class DSMLiteratureReview(Dataset[dict[str, pd.DataFrame]]):
    """Demand-shiftability category of industrial products from the literature."""

    name = "dsm_literature_review"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Demand-shiftability of industrial products, literature review",
            author=["Goericke, H."],
            publication="docs/files/user_guide/industry.md",
            publication_year=2026,
            note=(
                "Based on Golmohamadi (2021), doi:10.1016/j.rser.2021.111963, and "
                "Boldrini et al. (2024), doi:10.1016/j.rser.2023.113988."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "industry"

    def _set_data(self) -> dict[str, pd.DataFrame]:
        # category per carrier (1 = not flexible, 2 = partially, 3 = fully
        # flexible) and the literature it is based on
        categories = pd.read_csv(
            self.path / "dsm_shiftability_categories.csv", index_col="carrier"
        )
        # storage cost (Euro/tproduct), opex (Euro/tproduct) and horizon (h)
        parameters = pd.read_csv(
            self.path / "dsm_category_parameters.csv", index_col="category"
        )
        return {"categories": categories, "parameters": parameters}

    def get_categories(self) -> pd.DataFrame:
        """Pessimistic and optimistic category per carrier."""
        return self.data["categories"][["pessimistic", "optimistic"]]

    def get_capex_specific_storage_energy(self, element: IndustryDSM) -> Attribute:
        """Storage cost of the carrier's category."""
        return element.capex_specific_storage_energy.set_data(
            default_value=self._get_cost(element, "capex"),
            unit=f"Euro/({element.power_unit}*h)",
            source=self._source(element),
        )

    def get_opex_specific_variable(self, element: IndustryDSM) -> Attribute:
        """Variable cost of the carrier's category."""
        return element.opex_specific_variable.set_data(
            default_value=self._get_cost(element, "opex"),
            unit=f"Euro/({element.power_unit}*h)",
            source=self._source(element),
        )

    def get_energy_to_power_ratio_max(self, element: IndustryDSM) -> Attribute:
        """Shifting horizon of the carrier's category."""
        return element.energy_to_power_ratio_max.set_data(
            default_value=self._get_parameters(element)["energy_to_power_ratio_max"],
            unit="h",
            source=self._source(element),
        )

    def get_capacity_limit(self, element: IndustryDSM) -> Attribute:
        """Stock limited to the product's demand, 0 at nodes without demand."""
        demand = element.model.elements[element.carrier].demand.df
        demand = demand if demand.ndim == 1 else demand.iloc[:, 0]
        nodes = list(model_nodes(element))
        nodes += [node for node in demand.index if node not in nodes]
        limit = (
            demand.reindex(pd.Index(nodes, name=demand.index.name))
            .fillna(0.0)
            .rename("capacity_limit")
        )
        return element.capacity_limit.set_data(
            default_value=np.inf,
            unit=element.power_unit,
            df=limit.to_frame(),
            source=AssumptionInformation(description="Stock up to the product demand."),
        )

    def _get_cost(self, element: IndustryDSM, parameter: str) -> float:
        """Cost per tonne, per GWh for the carriers modeled on an energy basis."""
        cost = self._get_parameters(element)[parameter]
        if element.carrier not in ENERGY_CONTENT:
            return cost
        return cost / ENERGY_CONTENT[element.carrier]

    def _get_category(self, element: IndustryDSM) -> int:
        shiftability = element.settings.industry_flexibility.dsm_shiftability
        return int(self.data["categories"].at[element.carrier, shiftability])

    def _get_parameters(self, element: IndustryDSM) -> dict[str, float]:
        parameters = self.data["parameters"].loc[self._get_category(element)]
        return {
            parameter: float(parameters[parameter])
            for parameter in ("capex", "opex", "energy_to_power_ratio_max")
        }

    def _source(self, element: IndustryDSM) -> AssumptionInformation:
        shiftability = element.settings.industry_flexibility.dsm_shiftability
        category = self._get_category(element)
        reference = self.data["categories"].at[element.carrier, "reference"]
        return AssumptionInformation(
            description=(
                f"{element.carrier}: demand-shiftability category {category} "
                f"({shiftability}, setting industry_flexibility.dsm_shiftability), "
                f"from a literature review: {reference}. The storage cost, "
                "variable cost and shifting horizon of the category are own "
                "assumptions, see docs, 'Demand-side management'."
            ),
        )
