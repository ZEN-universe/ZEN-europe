from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

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

# internal (technology, scenario) -> EUREF technology-row label. Technologies
# with only one EUREF row (no min/max split) are keyed with scenario=None and
# used as a fallback for every scenario, matching the source's structure.
_TECHS: dict[tuple[str, str | None], str] = {
    ("wind_onshore", "min"): "Wind onshore - very high resource area, low hub height",
    ("wind_onshore", "ref"): "Wind onshore - medium resource area, medium height",
    ("wind_onshore", "max"): "Wind onshore - low resource area, high hub height",
    (
        "wind_offshore",
        "min",
    ): "Wind-offshore - shallow waters, distant from shore, high resource area",
    (
        "wind_offshore",
        "ref",
    ): "Wind-offshore - deep waters, distant from shore, high resource area",
    (
        "wind_offshore",
        "max",
    ): "Wind-offshore - deep waters, distant from shore, low resource area",
    (
        "wind_offshore_near_shore",
        "min",
    ): "Wind-offshore - shallow waters, near-shore, high resource area",
    (
        "wind_offshore_near_shore",
        "ref",
    ): "Wind-offshore - deep waters, near-shore, high resource area",
    (
        "wind_offshore_near_shore",
        "max",
    ): "Wind-offshore - deep waters, near-shore, low resource area",
    ("photovoltaics", "min"): "Solar PV - utility-scale - high resource area",
    ("photovoltaics", "ref"): "Solar PV - utility-scale - medium resource area",
    ("photovoltaics", "max"): "Solar PV - utility-scale - low resource area",
    ("natural_gas_turbine", None): "Gas turbine combined cycle gas conventional",
    ("natural_gas_turbine_CCS", None): "Gas combined cycle CCS post combustion",
    ("hard_coal_plant", None): "Steam turbine coal conventional",
    ("hard_coal_plant_CCS", None): "Integrated gasification coal CCS pre combustion",
    ("lignite_coal_plant", None): "Steam turbine lignite conventional",
    ("biomass_plant", None): "Steam turbine biomass solid conventional",
    ("biomass_plant_CCS", None): "Steam turbine biomass solid conventional w. CCS",
    ("waste_plant", None): "Small waste burning plant",
    ("nuclear", "ref"): "Nuclear III gen. (incl. economies of scale)",
    ("nuclear", "max"): "Nuclear III gen. (no economies of scale)",
    ("natural_gas_boiler_DH", None): "District heating boilers gas",
    ("heat_pump_DH", None): "District heating heat pump",
    ("oil_boiler_DH", None): "District heating boilers fuel oil",
    ("waste_boiler_DH", None): "MBW incinerator district heating",
    ("biomass_boiler_DH", None): "District heating boilers biomass",
    ("hard_coal_boiler_DH", None): "District heating boilers coal",
    ("electrode_boiler_DH", None): "District heating electricity",
    ("run-of-river_hydro", None): "Run of river",
    ("reservoir_hydro", None): "Lakes",
}
_SCENARIOS = ("min", "ref", "max")
# column-block order in the source sheet: (our variable name, dict-column-index)
_COST_VARIABLE_SEGMENTS = {0: "capex", 1: "fopex", 2: "vopex"}
_TECH_VARIABLE_SEGMENTS = {3: "efficiency", 5: "lifetime"}
_MONEY_YEAR_SRC = 2020


def _lookup_euref_technology(technology: str, scenario: str) -> str | None:
    if (technology, scenario) in _TECHS:
        return _TECHS[(technology, scenario)]
    if (technology, None) in _TECHS:
        return _TECHS[(technology, None)]
    return None


class EUREF(Dataset[pd.DataFrame]):
    """EU Reference Scenario 2020 power & heat technology assumptions.

    This class implements the specific behavior for the EUREF dataset.
    """

    name = "euref"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "EU Reference Scenario 2020 - Technology Assumptions for the Power "
                "and Heat Sector"
            ),
            author=["European Commission"],
            publication="European Commission, DG Energy",
            publication_year=2021,
            url="https://energy.ec.europa.eu/data-and-analysis/energy-modelling/eu-reference-scenario-2020_en",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "cost" / "euref"

    def _set_data(self) -> pd.DataFrame:
        raw = pd.read_excel(
            self.path / "REF2020_Technology Assumptions_Energy.xlsx",
            sheet_name="Power&Heat",
            header=1,
        )
        raw.columns = raw.columns.astype(str).str.replace("\n", "")
        segment_starts = np.where(~raw.iloc[0].isna())[0].tolist()
        techs = raw.iloc[2:, 0].reset_index(drop=True)

        rows: list[tuple[Any, int | None, str, float, str, float]] = []
        for segment_idx, segment_start in enumerate(segment_starts):
            segment_end = (
                segment_starts[segment_idx + 1]
                if segment_idx + 1 < len(segment_starts)
                else len(raw.columns) + 1
            )
            unit_src = cast(str, raw.iloc[0, segment_start])

            if segment_idx in _COST_VARIABLE_SEGMENTS:
                variable = _COST_VARIABLE_SEGMENTS[segment_idx]
                years = [int(y) for y in raw.iloc[1, segment_start:segment_end]]
                block = raw.iloc[2:, segment_start:segment_end].reset_index(drop=True)
                block.index = techs
                multiplier = _convert_unit(unit_src, variable)
                schema_unit = {
                    "capex": "Euro/kW",
                    "fopex": "Euro/kW",
                    "vopex": "Euro/MWh",
                }[variable]
                for tech_row, values in block.iterrows():
                    for year, value_src in zip(years, values, strict=True):
                        value_src = pd.to_numeric(value_src, errors="coerce")
                        if pd.isna(value_src):
                            continue
                        rows.append(
                            (
                                tech_row,
                                year,
                                variable,
                                float(value_src) * multiplier,
                                schema_unit,
                                float(value_src),
                            )
                        )
            elif segment_idx in _TECH_VARIABLE_SEGMENTS:
                variable = _TECH_VARIABLE_SEGMENTS[segment_idx]
                # efficiency/lifetime have a single value per technology (no year
                # breakdown)
                values = raw.iloc[2:, segment_start].reset_index(drop=True)
                schema_unit = "-" if variable == "efficiency" else "1"
                for tech_row, value_src in zip(techs, values, strict=True):
                    value_src = pd.to_numeric(value_src, errors="coerce")
                    if pd.isna(value_src):
                        continue
                    rows.append(
                        (
                            tech_row,
                            None,
                            variable,
                            float(value_src),
                            schema_unit,
                            float(value_src),
                        )
                    )

        by_euref_tech: dict[tuple, list] = {}
        for tech_row, row_year, variable, value, unit, value_src in rows:
            by_euref_tech.setdefault((tech_row, variable), []).append(
                (row_year, value, unit, value_src)
            )

        cost_years = sorted(
            {
                year
                for (_, var), entries in by_euref_tech.items()
                if var in _COST_VARIABLE_SEGMENTS.values()
                for year, *_ in entries
            }
        )

        out_rows: list[tuple[Any, ...]] = []
        for technology in {t for t, _ in _TECHS}:
            for scenario in _SCENARIOS:
                euref_tech = _lookup_euref_technology(technology, scenario)
                if euref_tech is None:
                    continue
                for variable in ("capex", "fopex", "vopex"):
                    entries = by_euref_tech.get((euref_tech, variable))
                    if not entries:
                        continue
                    for year, value, unit, value_src in entries:
                        out_rows.append(
                            (
                                technology,
                                "M",
                                scenario,
                                variable,
                                year,
                                value,
                                unit,
                                _MONEY_YEAR_SRC,
                                value_src,
                                unit,
                            )
                        )
                for variable in ("efficiency", "lifetime"):
                    entries = by_euref_tech.get((euref_tech, variable))
                    if not entries:
                        continue
                    _, value, unit, value_src = entries[0]
                    for year in cost_years:
                        out_rows.append(
                            (
                                technology,
                                "M",
                                scenario,
                                variable,
                                year,
                                value,
                                unit,
                                None,
                                value_src,
                                unit,
                            )
                        )
        data = pd.DataFrame(out_rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        data = data.drop_duplicates(subset=INDEX_NAMES)
        return data.set_index(INDEX_NAMES).sort_index()

    # -------- methods ------------------------

    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized EUREF cost/tech data (see `_cost_schema`)."""
        return self.data.copy()


def _convert_unit(unit_src: str, variable: str) -> float:
    """Multiplier from an EUREF source unit to this package's standard unit."""
    if variable in ("capex", "fopex") and unit_src == "EUR/kW":
        return 1.0
    if variable == "vopex" and unit_src == "EUR/MWh":
        return 1.0
    raise ValueError(f"Unexpected EUREF unit '{unit_src}' for variable '{variable}'")
