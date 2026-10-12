from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial._cost_schema import (
    CO2_BASIS_UNITS,
    INDEX_NAMES,
    VALUE_COLUMNS,
)
from zen_europe.utils.constants import Constants

# internal technology name -> LUW technology label. DAC is reported on a
# tCO2 basis rather than the power/heat Euro/kW schema used by every other
# technology here (same CO2_BASIS_UNITS convention as DEA's CCS technologies,
# see dea.py); it is special-cased in `_set_data` accordingly.
_TECHS: dict[str, str] = {
    "wind_onshore": "Wind onshore PP",
    # NOTE: the LUW source data maps offshore wind to the same "Wind onshore
    # PP" row as onshore wind (verified against the original spreadsheet;
    # LUW has no separate offshore entry), so we do not port wind_offshore.
    "photovoltaics": "PV fixed tilted PP",
    "rooftop_photovoltaics": "PV rooftop -residential",
    "rooftop_photovoltaics_com": "PV rooftop -industrial",
    "run-of-river_hydro": "Hydro Run-of-River PP",
    "reservoir_hydro": "Hydro Reservoir/ Dam",
    "natural_gas_turbine": "CCGT PP",
    "natural_gas_turbine_CCS": "CCGT PP + CCS",
    "oc_natural_gas_turbine": "OCGT PP",
    "hard_coal_plant": "Coal PP",
    "nuclear": "Nuclear PP",
    "biomass_plant": "Biomass PP",
    "waste_plant": "MSW incinerator",
    "heat_pump": "Local Heat Pump",
    "electrode_boiler": "Local Electric Heating",
    "natural_gas_boiler": "Local NG Heating",
    "oil_boiler": "Local Oil Heating",
    "biomass_boiler": "Local Biomass Heating",
    "heat_pump_DH": "DH Heat Pump",
    "electrode_boiler_DH": "DH Electric Heating",
    "natural_gas_boiler_DH": "DH NG Heating",
    "oil_boiler_DH": "DH Oil Heating",
    "hard_coal_boiler_DH": "DH Coal Heating",
    "biomass_boiler_DH": "DH Biomass Heating",
    "electrolysis": "Water Electrolysis",
    "fischer_tropsch": "Fischer-Tropsch unit",
    "methanation": "Methanation",
    "SMR": "Steam Methane Reforming",
    "DAC": "CO_{2} direct air capture",
}
_VARIABLES: dict[str, str] = {
    "capex": "Capex",
    "fopex": "Opex fix",
    "vopex": "Opex var",
}
_MONEY_YEAR_SRC = 2020


def _clean_unit(unit: str) -> str:
    """Normalize the LaTeX-ish LUW unit strings (`€/kW_{el}`, `€/(kW_{el} a)`, ...)."""
    return (
        unit.replace("_{el}", "")
        .replace("_{th}", "")
        .replace("(kW a)", "kW")
        .replace("(kW)", "kW")
        .replace("kWel", "kWh")
    )


def _convert_to_schema_unit(unit_src: str, variable: str) -> float:
    """Multiplier from a cleaned LUW unit to this package's standard unit.

    LUW reports capex/fopex on a `€/kW*` basis (electric-, H2-, SNG- or
    liquid-fuel-equivalent kW, all treated as generically "kW" here, matching
    the legacy script's simplification) and vopex on a `€/kWh*` (or, for SNG,
    already `€/MWh`) basis.
    """
    if variable in ("capex", "fopex"):
        if "kW" in unit_src and "kWh" not in unit_src:
            return 1.0
        raise ValueError(f"Unexpected LUW {variable} unit '{unit_src}'")
    if variable == "vopex":
        if "kWh" in unit_src:
            return 1000.0  # Euro/kWh -> Euro/MWh
        if "MWh" in unit_src:
            return 1.0
        raise ValueError(f"Unexpected LUW vopex unit '{unit_src}'")
    raise ValueError(f"Unexpected LUW variable '{variable}'")


def _convert_dac_unit(unit_src: str, variable: str) -> float:
    """Multiplier from a LUW DAC source unit to `CO2_BASIS_UNITS`.

    DAC's capex/fopex are reported per annual tCO2 capacity (`€/(t_{CO2} a)`);
    `CO2_BASIS_UNITS` uses a per-hour-throughput basis, so multiply by 8760
    (hours/year) to convert. vopex is already on a per-tCO2 basis.
    """
    if variable in ("capex", "fopex") and unit_src == "€/(t_{CO2} a)":
        return Constants.HOURS_PER_YEAR
    if variable == "vopex" and unit_src == "€/t_{CO2}":
        return 1.0
    raise ValueError(f"Unexpected LUW DAC unit '{unit_src}' for variable '{variable}'")


class LUW(Dataset[pd.DataFrame]):
    """LUT/EWG "Low-Cost Renewable Energy" (LUW) power/heat/PtX cost data.

    This class implements the specific behavior for the LUW dataset.
    """

    name = "luw"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Reflecting the energy transition from a European perspective and in "
                "the global context—Relevance of solar photovoltaics benchmarking two "
                "ambitious scenarios"
            ),
            author=[
                "Christian Breyer",
                "Dmitrii Bogdanov",
                "Manish Ram",
                "Siavash Khalili",
                "Eero Vartiainen",
                "David Moser",
                "Eduardo Román Medina",
                "Gaetan Masson",
                "Arman Aghahosseini",
                "Theophilus N. O. Mensah" "Gabriel Lopez",
                "Michael Schmela",
                "Raffaele Rossi",
                "Walburga Hemetsberger",
                "Arnulf Jaeger-Waldau",
            ],
            publication="Progress in Photovoltaics",
            publication_year=2022,
            url="https://onlinelibrary.wiley.com/doi/10.1002/pip.3659",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "cost" / "luw"

    def _set_data(self) -> pd.DataFrame:
        raw = pd.read_excel(self.path / "LUW_costs.xlsx", sheet_name="Append1")
        raw["Technologies"] = raw["Technologies"].ffill().str.replace("\n", " ")
        raw["Unit"] = raw["Unit"].apply(_clean_unit)
        raw = raw.drop(columns=["Sources"]).rename(columns={"Column1": "Variable"})
        raw = raw.set_index(["Technologies", "Variable", "Unit"])
        year_columns = [int(col) for col in raw.columns if str(col).isdigit()]
        raw.columns = [int(col) if str(col).isdigit() else col for col in raw.columns]

        rows: list[tuple[Any, ...]] = []
        for technology, luw_tech in _TECHS.items():
            if luw_tech not in raw.index.get_level_values("Technologies"):
                continue
            tech_rows = raw.loc[luw_tech]
            for variable, luw_variable in _VARIABLES.items():
                if luw_variable not in tech_rows.index.get_level_values("Variable"):
                    continue
                sel = tech_rows.loc[luw_variable]
                unit_src = cast(
                    str, sel.index[0] if isinstance(sel, pd.DataFrame) else sel.name
                )
                values = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel
                if technology == "DAC":
                    multiplier = _convert_dac_unit(unit_src, variable)
                    schema_unit = CO2_BASIS_UNITS[variable]
                else:
                    multiplier = _convert_to_schema_unit(unit_src, variable)
                    schema_unit = (
                        "Euro/MWh"
                        if variable == "vopex"
                        else ("Euro/kW" if variable == "capex" else "Euro/kW")
                    )
                for year in year_columns:
                    value_src = values[year]
                    if pd.isna(value_src):
                        continue
                    rows.append(
                        (
                            technology,
                            "M",
                            "ref",
                            variable,
                            year,
                            float(value_src) * multiplier,
                            schema_unit,
                            _MONEY_YEAR_SRC,
                            float(value_src),
                            unit_src,
                        )
                    )
            if "Lifetime" in tech_rows.index.get_level_values("Variable"):
                lt_sel = tech_rows.loc["Lifetime"]
                lt_unit = (
                    lt_sel.index[0] if isinstance(lt_sel, pd.DataFrame) else lt_sel.name
                )
                lt_values = (
                    lt_sel.iloc[0] if isinstance(lt_sel, pd.DataFrame) else lt_sel
                )
                for year in year_columns:
                    value_src = lt_values[year]
                    if pd.isna(value_src):
                        continue
                    rows.append(
                        (
                            technology,
                            "M",
                            "ref",
                            "lifetime",
                            year,
                            float(value_src),
                            "1",
                            None,
                            float(value_src),
                            lt_unit,
                        )
                    )
        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        return data.set_index(INDEX_NAMES).sort_index()

    # -------- methods ------------------------

    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized LUW cost/tech data (see `_cost_schema`)."""
        return self.data.copy()
