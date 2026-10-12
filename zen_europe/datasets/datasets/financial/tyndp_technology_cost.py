from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

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
# our scenario -> TYNDP scenario. TYNDP's own source data assigns a different
# mapping for "photovoltaics", but that technology never appears in `_TECHS`
# (only the rooftop variants do, which use the general mapping below), so a
# single mapping is sufficient here.
_SCENARIOS: dict[str, str] = {"min": "GA", "max": "NT", "ref": "DE"}
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
                for scenario, tyndp_scenario in _SCENARIOS.items():
                    sel = tech_rows[
                        (tech_rows["Variable"] == tyndp_variable)
                        & (tech_rows["Scenario"] == tyndp_scenario)
                    ]
                    if sel.empty:
                        continue
                    unit_src = sel["Unit"].iloc[0]
                    assert unit_src == _SOURCE_UNIT, (
                        f"Unexpected TYNDP unit '{unit_src}' for "
                        f"{tyndp_technology}/{tyndp_variable} (expected "
                        f"'{_SOURCE_UNIT}')"
                    )
                    for year in year_columns:
                        value_src = sel[year].iloc[0]
                        if pd.isna(value_src):
                            continue
                        rows.append(
                            (
                                technology,
                                "M",
                                scenario,
                                variable,
                                year,
                                float(
                                    value_src
                                ),  # kEuro/MW == Euro/kW (and Euro/kW for fopex)
                                "Euro/kW" if variable == "capex" else "Euro/kW",
                                _MONEY_YEAR_SRC,
                                float(value_src),
                                unit_src,
                            )
                        )
        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        return data.set_index(INDEX_NAMES).sort_index()

    # -------- methods ------------------------

    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized TYNDP cost data (see `_cost_schema`)."""
        return self.data.copy()
