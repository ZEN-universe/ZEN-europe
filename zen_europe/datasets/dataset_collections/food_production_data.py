from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import AssumptionInformation

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.datasets.datasets.carrier.faostat_food import FAOSTATFood
from zen_europe.datasets.datasets.carrier.rehfeldt2017 import Rehfeldt2017
from zen_europe.utils.constants import Constants
from zen_europe.utils.industry import DATA_YEAR, model_nodes
from zen_europe.utils.utils import instance_cache

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings

SECTOR = "food"
# FAOSTAT item of each Rehfeldt (2017) food sub-process
FOOD_ITEMS = {
    "dairy": "Milk, Total",
    "meat_processing": "Meat, Total",
    "brewing": "Beer of barley, malted",
    "bread_bakery": "Wheat",
    "sugar": "Raw cane or beet sugar (centrifugal only)",
}


class FoodProductionData(DatasetCollection):
    """Food production: demand, energy intensity, capacity and costs."""

    name = "food_production_data"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "industry_production_data": IndustryProductionData(
                self.settings, self.source_path
            ),
            "rehfeldt2017": Rehfeldt2017(self.source_path),
            "faostat_food": FAOSTATFood(self.source_path),
        }

    # ---------- product ----------

    def get_demand(self, element: Element) -> Attribute:
        """Get the food demand: today's production."""
        return self._industry.get_demand(
            element,
            self.calculate_production(model_nodes(element)),
            "The production is the Rehfeldt et al. (2017) activity of the food "
            "sub-processes, split to the nodes by the FAOSTAT production of a proxy "
            "item per sub-process.",
        )

    # ---------- production technology ----------

    def get_input_carrier(self, element: Element) -> Attribute:
        """Get the input carriers of food production."""
        return self._industry.get_input_carrier(
            element,
            self.calculate_conversion_factors(),
            "The fuels are the JRC-IDEES thermal energy carriers of food above the "
            "fuel share cut-off.",
        )

    def get_conversion_factor(self, element: Element) -> Attribute:
        """Get the energy demand per tonne of food."""
        return self._industry.get_conversion_factor(
            element,
            self.calculate_conversion_factors(),
            "The energy intensity is the activity-weighted energy intensity of the "
            "food sub-processes from Rehfeldt et al. (2017); the fuel above 200 °C "
            "is split by the JRC-IDEES fuel mix.",
        )

    def get_capacity_existing(self, element: Element) -> Attribute:
        """Get the existing food production capacity."""
        industry = self._industry
        return industry.get_capacity_existing(
            element,
            self.calculate_production(model_nodes(element))
            / industry.capacity_utilisation,
            "The existing production capacity is the production divided by "
            f"{industry.describe_capacity_utilisation()}.",
        )

    def get_lifetime(self, element: Element) -> Attribute:
        """Get the lifetime from the literature."""
        return element.lifetime.set_data(
            default_value=self._industry.calculate_literature_cost(SECTOR, "lifetime"),
            source=self._literature_source("lifetime"),
        )

    def get_capex_specific_conversion(self, element: Element) -> Attribute:
        """Get the investment cost from the literature."""
        capex = self._industry.calculate_literature_cost(SECTOR, "capex")
        return element.capex_specific_conversion.set_data(
            # Euro/(t/a) -> Euro/(t/h)
            default_value=round(capex * Constants.HOURS_PER_YEAR, 2),
            unit="Euro/(tproduct/h)",
            source=self._literature_source("capex"),
        )

    def get_opex_specific_fixed(self, element: Element) -> Attribute:
        """Get the fixed O&M cost from the literature."""
        opex = self._industry.calculate_literature_cost(SECTOR, "opex_fixed")
        return element.opex_specific_fixed.set_data(
            # Euro/(t/a) -> Euro/(t/h)
            default_value=round(opex * Constants.HOURS_PER_YEAR, 2),
            unit="Euro/(tproduct/h)",
            source=self._literature_source("opex_fixed"),
        )

    def get_opex_specific_variable(self, element: Element) -> Attribute:
        """Get the variable O&M cost from the literature, without energy."""
        return element.opex_specific_variable.set_data(
            default_value=self._industry.calculate_literature_cost(
                SECTOR, "opex_variable"
            ),
            unit="Euro/tproduct",
            source=self._literature_source("opex_variable"),
        )

    # ---------- data used by other collections ----------

    @instance_cache
    def calculate_production(self, nodes: tuple[str, ...]) -> pd.Series:
        """Food production (t/h): Rehfeldt (2017) activity split by FAOSTAT
        production."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        faostat = cast(FAOSTATFood, self.data["faostat_food"])
        activity = rehfeldt.get_sub_processes(SECTOR).loc[
            list(FOOD_ITEMS), "activity_Mt"
        ]
        production = faostat.get_production(DATA_YEAR)
        production = production.reindex(
            index=list(FOOD_ITEMS.values()),
            columns=list(nodes),
            fill_value=0.0,
        )
        production.index = list(FOOD_ITEMS)
        shares = production.div(production.sum(axis=1), axis=0).fillna(0.0)
        activity = shares.mul(activity, axis=0).sum()  # Mt/a
        return activity * 1e6 / Constants.HOURS_PER_YEAR  # Mt/a -> t/h

    def calculate_demand(self, nodes: tuple[str, ...]) -> pd.Series:
        """Food demand (t/h): the production."""
        return self.calculate_production(nodes).rename("demand").rename_axis("node")

    def calculate_energy_intensity(self) -> pd.Series:
        """Fuel (above 200 °C), heat and electricity demand (GW per t/h) from the
        Rehfeldt et al. (2017) sub-processes."""
        return self._energy_intensity

    def calculate_heat_conversion_factors(self) -> pd.Series:
        """Heat demand per band (GW per t/h)."""
        return self._industry.calculate_heat_conversion_factors(
            SECTOR, self.calculate_energy_intensity()
        )

    def calculate_fuel_shares(self) -> pd.Series:
        """JRC-IDEES fuel mix of food."""
        return self._industry.calculate_fuel_shares(SECTOR)

    def calculate_conversion_factors(self) -> pd.Series:
        """Energy demand (GW per t/h) per input carrier."""
        return self._industry.calculate_conversion_factors(
            SECTOR, self.calculate_energy_intensity(), self.calculate_fuel_shares()
        )

    # ---------- helpers ----------

    @property
    def _industry(self) -> IndustryProductionData:
        return cast(IndustryProductionData, self.data["industry_production_data"])

    @cached_property
    def _energy_intensity(self) -> pd.Series:
        return self._industry.calculate_energy_intensity_rehfeldt(SECTOR)

    def _literature_source(self, parameter: str) -> AssumptionInformation:
        return AssumptionInformation(
            description=(
                self._industry.describe_literature_cost(SECTOR, parameter)
                + " "
                + self._industry.describe_inflation()
            )
        )
