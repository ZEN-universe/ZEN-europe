from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import numpy as np
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial._cost_schema import (
    INDEX_NAMES,
    VALUE_COLUMNS,
)

# internal technology name -> TYNDP technology label
_TECHS: dict[str, str] = {
    "wind_onshore": "Wind on-shore",
    "wind_offshore": "Wind off-shore",
    "rooftop_photovoltaics": "Solar PV (residential)",
    "photovoltaics": "Solar PV (commercial)",
    "natural_gas_turbine": "CCGT",
    "oc_natural_gas_turbine": "OCGT",
}
# TYNDP scenarios. They are storylines, not cost bounds, and which one is the
# cheapest depends on the technology (e.g., DE for solar PV, GA for wind), so they
# are ranked per technology, variable and year instead of mapped to our scenarios
# (see `_rank_scenarios`).
_TYNDP_SCENARIOS: tuple[str, ...] = ("NT", "GA", "DE")
# our scenarios in order of increasing value
_RANKED_SCENARIOS: tuple[str, ...] = ("min", "ref", "max")
# our variable -> TYNDP variable label. TYNDP has no variable OPEX figures.
_VARIABLES: dict[str, str] = {"capex": "CAPEX", "fopex": "FIXED VOM"}
_MONEY_YEAR_SRC = 2020
_SOURCE_UNIT = "TEUR/MW"


class TYNDPTechnologyCost(Dataset[pd.DataFrame]):
    """TYNDP 2020 scenario-building technology cost assumptions.

    This class implements the specific behavior for the TYNDP cost dataset.
    """

    name = "tyndp_technology_cost"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="TYNDP 2020 Scenario Building Guidelines - Cost Assumptions",
            author=["ENTSOG", "ENTSO-E"],
            publication="ENTSOG/ENTSO-E",
            publication_year=2020,
            url=(
                "https://2020.entsos-tyndp-scenarios.eu/wp-content/uploads/2020/07/"
                "TYNDP_2020_Scenario_Building-Guidelines_03_Annex_2_Cost_Assumptions_final_report.pdf"
            ),
            note=(
                "Cost figures transcribed into TYNDP_cost_assumptions.xlsx from the "
                "PDF above."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "cost" / "tyndp"

    def _set_data(self) -> pd.DataFrame:
        raw = pd.read_excel(self.path / "TYNDP_cost_assumptions.xlsx")
        year_columns = [col for col in raw.columns if isinstance(col, int)]

        rows = []
        for technology, tyndp_technology in _TECHS.items():
            tech_rows = raw[raw["Technology"] == tyndp_technology]
            for variable, tyndp_variable in _VARIABLES.items():
                sel = tech_rows[tech_rows["Variable"] == tyndp_variable]
                if sel.empty:
                    continue
                unit_src = sel["Unit"].iloc[0]
                assert (sel["Unit"] == _SOURCE_UNIT).all(), (
                    f"Unexpected TYNDP unit '{unit_src}' for "
                    f"{tyndp_technology}/{tyndp_variable} (expected "
                    f"'{_SOURCE_UNIT}')"
                )
                ranked = self._rank_scenarios(
                    sel.set_index("Scenario")[year_columns], tyndp_technology
                )
                for (scenario, year), value_src in ranked.stack().items():
                    rows.append(
                        (
                            technology,
                            "M",
                            scenario,
                            variable,
                            year,
                            float(value_src),  # kEuro/MW == Euro/kW
                            "Euro/kW",
                            _MONEY_YEAR_SRC,
                            float(value_src),
                            unit_src,
                        )
                    )
        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        return data.set_index(INDEX_NAMES).sort_index()

    @staticmethod
    def _rank_scenarios(values: pd.DataFrame, tyndp_technology: str) -> pd.DataFrame:
        """Rank the TYNDP scenarios per year into our min, ref and max scenarios.

        The lowest of the three scenario values is min, the middle one ref and the
        highest max, so min and max bound the TYNDP range like the lower and upper
        estimates of the other agencies, and the mean and median across the
        scenarios are unchanged. NT ends in 2040; its 2040 value is carried over to
        2050, as the interpolation in `TechnologyCostDatabase` did before.
        """
        values = values.reindex(list(_TYNDP_SCENARIOS)).astype(float).ffill(axis=1)
        assert values.notna().all().all(), (
            f"Missing TYNDP scenario values for {tyndp_technology}:\n{values}"
        )
        ranked = np.sort(values.to_numpy(), axis=0)
        return pd.DataFrame(
            ranked, index=list(_RANKED_SCENARIOS), columns=values.columns
        )

    # -------- methods ------------------------

    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized TYNDP cost data (see `_cost_schema`)."""
        return self.data.copy()
