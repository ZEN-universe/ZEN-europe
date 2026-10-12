from __future__ import annotations

from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
from zen_creator import Attribute, SourceInformation, StorageTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial._cost_schema import (
    INDEX_NAMES,
    STANDARD_UNITS,
    VALUE_COLUMNS,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro


class StorageTechnologiesSchmidt(Dataset[pd.DataFrame]):
    """
    Electricity storage technologies dataset class from Schmidt et al. (2019).

    Provides the capex of the power and of the energy capacity, the fixed opex,
    the lifetime, the construction time and the round-trip efficiency of
    electricity storage technologies. Table S4 of the study reports the input
    parameters for 2015 and table S8 the investment cost of the later years
    relative to 2015, so a cost of a given year is the product of the two.

    The round-trip efficiency is split evenly between charging and discharging.
    Assume that reservoir hydro and pumped hydro have the same lifetime,
    construction time and round-trip efficiency.
    """

    name = "storage_technologies_schmidt"

    MONEY_YEAR = 2015
    MONEY_UNIT = "USD"

    # Table S4, technology input parameters for 2015. The investment cost is
    # reported per unit of power [USD/kW] and of energy [USD/kWh], the
    # operation cost per unit of power and year [USD/kW/year].
    COST_2015: dict[str, dict[str, float]] = {
        "battery": {"capex": 678, "capex_energy": 802, "fopex": 10},
        "pumped_hydro": {"capex": 1129, "capex_energy": 80, "fopex": 8},
    }

    # Table S8, investment cost projections relative to 2015. Pumped hydro
    # gets more expensive over time, since the favourable sites are built first.
    RELATIVE_COST: dict[str, dict[int, float]] = {
        "battery": {
            2015: 1.00,
            2020: 0.55,
            2025: 0.34,
            2030: 0.23,
            2035: 0.18,
            2040: 0.16,
            2045: 0.15,
            2050: 0.14,
        },
        "pumped_hydro": {
            2015: 1.00,
            2020: 1.00,
            2025: 1.00,
            2030: 1.00,
            2035: 1.01,
            2040: 1.01,
            2045: 1.02,
            2050: 1.02,
        },
    }

    # Table S4, shelf life [years]
    LIFETIMES = {
        "battery": 13,
        "pumped_hydro": 55,
        "reservoir_hydro": 55,
    }
    # Table S4, construction time [years]
    CONSTRUCTION_TIMES = {
        "battery": 1,
        "pumped_hydro": 3,
        "reservoir_hydro": 3,
    }
    # Table S4, round-trip efficiency
    EFFICIENCIES_ROUND_TRIP = {
        "battery": 0.86,
        "pumped_hydro": 0.78,
        "reservoir_hydro": 0.78,
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Projecting the Future Levelized Cost of Electricity Storage "
                "Technologies"
            ),
            author=[
                "Oliver Schmidt",
                "Sylvain Melchior",
                "Adam Hawkes",
                "Iain Staffell",
            ],
            publication="Joule",
            publication_year=2019,
            doi="https://doi.org/10.1016/j.joule.2018.12.008",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        rows = []
        for technology, costs in self.COST_2015.items():
            for variable, cost_2015 in costs.items():
                for year, relative in self.RELATIVE_COST[technology].items():
                    rows.append(
                        (
                            technology,
                            "M",
                            "ref",
                            variable,
                            int(year),
                            float(cost_2015 * relative),
                            STANDARD_UNITS[variable],
                            self.MONEY_YEAR,
                            float(cost_2015 * relative),
                            self._source_unit(variable),
                        )
                    )
        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        return data.set_index(INDEX_NAMES).sort_index()

    def _source_unit(self, variable: str) -> str:
        """The unit table S4 reports `variable` in."""
        return STANDARD_UNITS[variable].replace("Euro", self.MONEY_UNIT)

    @cached_property
    def _costs_in_euro(self) -> pd.DataFrame:
        """
        The cost data converted from US dollars to euros of the same money year.

        The exchange rate is only looked up once the costs are actually
        requested, so that the lifetime, construction time and efficiency stay
        available without it.
        """
        dollar2euro = ECBDollar2Euro(source_path=self.source_path)
        data = self.data.copy()
        data["value"] *= data["money_year_src"].map(
            lambda money_year: dollar2euro.get_dollar2euro(int(money_year))
        )
        return data

    # -------- methods ------------------------
    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized cost data (see `_cost_schema`)."""
        return self._costs_in_euro.copy()

    def get_lifetime(self, technology: StorageTechnology) -> Attribute:
        """
        Get the lifetime of a storage technology.
        """
        lifetime = self._get_value(self.LIFETIMES, technology, "lifetime")
        attr = technology.lifetime
        return attr.set_data(
            default_value=lifetime,
            source=SourceInformation(
                description=(
                    f"The lifetime of {technology.name} is based on "
                    "Schmidt et al. (2019)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_construction_time(self, technology: StorageTechnology) -> Attribute:
        """
        Get the construction time of a storage technology.
        """
        construction_time = self._get_value(
            self.CONSTRUCTION_TIMES, technology, "construction time"
        )
        attr = technology.construction_time
        return attr.set_data(
            default_value=construction_time,
            source=SourceInformation(
                description=(
                    f"The construction time of {technology.name} is based on "
                    "Schmidt et al. (2019)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_efficiency_charge(self, technology: StorageTechnology) -> Attribute:
        """
        Get the charging efficiency of a storage technology.
        """
        return self._set_efficiency(technology, technology.efficiency_charge)

    def get_efficiency_discharge(self, technology: StorageTechnology) -> Attribute:
        """
        Get the discharging efficiency of a storage technology.
        """
        return self._set_efficiency(technology, technology.efficiency_discharge)

    def _set_efficiency(
        self, technology: StorageTechnology, attr: Attribute
    ) -> Attribute:
        """
        Set an efficiency attribute to half of the round-trip efficiency.
        """
        efficiency_round_trip = self._get_value(
            self.EFFICIENCIES_ROUND_TRIP, technology, "round-trip efficiency"
        )
        return attr.set_data(
            default_value=np.sqrt(efficiency_round_trip),
            unit="1",
            source=SourceInformation(
                description=(
                    f"The round-trip efficiency of {technology.name} is "
                    f"{efficiency_round_trip} in Schmidt et al. (2019) and is "
                    "split evenly between charging and discharging."
                ),
                metadata=self.metadata,
            ),
        )

    @staticmethod
    def _get_value(
        values: dict[str, float],
        technology: StorageTechnology,
        variable: str,
    ) -> float:
        """
        Get the value of a variable for a technology.
        """
        if technology.name not in values:
            raise ValueError(
                f"The {variable} of technology '{technology.name}' is not "
                f"available in the dataset '{StorageTechnologiesSchmidt.name}'."
            )
        return values[technology.name]
