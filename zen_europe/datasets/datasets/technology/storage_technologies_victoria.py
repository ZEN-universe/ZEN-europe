from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial._cost_schema import (
    INDEX_NAMES,
    STANDARD_UNITS,
    VALUE_COLUMNS,
)


class StorageTechnologiesVictoria(Dataset[pd.DataFrame]):
    """
    Electricity storage technologies dataset class from Victoria et al. (2022).

    Provides the capex of the power and of the energy capacity and the fixed
    opex of the storage technologies. Table S1 of the study reports the
    overnight investment cost per component in real 2015 euros, table S2 the
    fixed operation and maintenance cost as a share of that investment cost per
    year.

    A storage technology of the model combines two of these components, one
    rated by power and one rated by energy. A battery combines a battery
    inverter with a battery cell stack, while the underground hydrogen storage
    of a salt cavern is rated by energy alone.
    """

    name = "storage_technologies_victoria"

    MONEY_YEAR = 2015

    # Table S1, overnight investment cost in real 2015 euros. The battery
    # inverter is rated by power [Euro/kW], the battery storage and the
    # underground hydrogen storage by energy [Euro/kWh].
    OVERNIGHT_COST: dict[str, dict[int, float]] = {
        "battery_inverter": {
            2020: 270,
            2025: 215,
            2030: 160,
            2035: 130,
            2040: 100,
            2045: 80,
            2050: 60,
        },
        "battery_storage": {
            2020: 232,
            2025: 187,
            2030: 142,
            2035: 118,
            2040: 94,
            2045: 84,
            2050: 75,
        },
        "hydrogen_storage_underground": {
            2020: 3.0,
            2025: 2.5,
            2030: 2.0,
            2035: 1.8,
            2040: 1.5,
            2045: 1.4,
            2050: 1.2,
        },
    }

    # Table S2, fixed operation and maintenance cost as a percentage of the
    # overnight investment cost per year.
    FIXED_OPEX_SHARE: dict[str, float] = {
        "battery_inverter": 0.2,
        "hydrogen_storage_underground": 0.0,
    }

    # model technology -> the component rated by power and the one rated by
    # energy. Table S1 reports the underground hydrogen storage per unit of
    # energy only, so the salt cavern has no power rated component.
    COMPONENTS: dict[str, tuple[str | None, str]] = {
        "battery": ("battery_inverter", "battery_storage"),
        "salt_cavern_storage": (None, "hydrogen_storage_underground"),
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Speed of technological transformations required in Europe to "
                "achieve different climate goals"
            ),
            author=[
                "Marta Victoria",
                "Elisabeth Zeyen",
                "Tom Brown",
            ],
            publication="Joule",
            publication_year=2022,
            doi="https://doi.org/10.1016/j.joule.2022.04.016",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        rows = []
        for technology, (power, energy) in self.COMPONENTS.items():
            power_cost = self.OVERNIGHT_COST.get(power, {}) if power else {}
            opex_share = self.FIXED_OPEX_SHARE.get(power, 0.0) if power else 0.0
            for year, cost_energy in self.OVERNIGHT_COST[energy].items():
                cost_power = power_cost.get(year, 0.0)
                rows.append(
                    self._row(
                        technology, "capex", year, cost_power, cost_power, "Euro/kW"
                    )
                )
                rows.append(
                    self._row(
                        technology,
                        "capex_energy",
                        year,
                        cost_energy,
                        cost_energy,
                        "Euro/kWh",
                    )
                )
                rows.append(
                    self._row(
                        technology,
                        "fopex",
                        year,
                        cost_power * opex_share / 100,
                        opex_share,
                        "%/year",
                    )
                )
        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        return data.set_index(INDEX_NAMES).sort_index()

    def _row(
        self,
        technology: str,
        variable: str,
        year: int,
        value: float,
        value_src: float,
        unit_src: str,
    ) -> tuple:
        """Build a single row of the cost schema."""
        return (
            technology,
            "M",
            "ref",
            variable,
            int(year),
            float(value),
            STANDARD_UNITS[variable],
            self.MONEY_YEAR,
            float(value_src),
            unit_src,
        )

    # -------- methods ------------------------
    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized cost data (see `_cost_schema`)."""
        return self.data.copy()
