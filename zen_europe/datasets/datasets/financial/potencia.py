from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.elements.technology import Technology
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.financial._cost_schema import (
    INDEX_NAMES,
    VALUE_COLUMNS,
    YEARS,
)

# internal technology name -> Potencia (Type, Technology, Size|None) row key.
# `Size=None` means the technology varies by plant_size, looked up dynamically using the
# plant_size letter ("S"/"M"/"L") directly as the raw file's own `Size` column value
# (Potencia
# has no separate size-name translator, unlike DEA); a fixed letter means the technology
# only
# exists at that one Potencia size. Co-generation is not part of this key: it is derived
# from
# whether "CCS" appears in the internal technology name (see `_cogen`), matching the
# legacy
# script's own logic.
#
# Not ported (documented limitations):
# - `solar_thermal`, `smr` ("Nuclear IV"): both exist in the raw file but neither
# technology
# is in `set_conversion_technologies.json`, so they're unused (same reasoning as DIW/LUW
#     dropping `solar_thermal`/`pumped_hydro`).
# - `pumped_hydro`: the legacy script's own mapping key ("Pumped storage") never matched
# the
# raw file's actual label ("Pump storage") -- this data was silently empty even when the
#     legacy script ran. Also not a modeled technology here, so moot either way.
_TECHS: dict[str, tuple[str, str, str | None]] = {
    "wind_onshore": ("Wind power plants", "Onshore", None),
    "wind_offshore": ("Wind power plants", "Offshore", None),
    "photovoltaics": ("Solar PV power plants", "Solar PV power plants", "L"),
    "rooftop_photovoltaics": ("Solar PV power plants", "Solar PV power plants", "S"),
    "rooftop_photovoltaics_com": (
        "Solar PV power plants",
        "Solar PV power plants",
        "M",
    ),
    "run-of-river_hydro": ("Hydro plants", "Run-of-river", None),
    "reservoir_hydro": ("Hydro plants", "Reservoirs (dams)", None),
    "natural_gas_turbine": (
        "Gas fired power plants (Natural gas, biogas)",
        "Gas turbine combined cycle",
        None,
    ),
    "natural_gas_turbine_CCS": (
        "Gas fired power plants (Natural gas, biogas)",
        "Gas turbine combined cycle",
        None,
    ),
    "oc_natural_gas_turbine": (
        "Gas fired power plants (Natural gas, biogas)",
        "Gas turbine",
        None,
    ),
    "hard_coal_plant": ("Coal fired power plants", "Supercritical steam turbine", None),
    "hard_coal_plant_CCS": (
        "Coal fired power plants",
        "Supercritical steam turbine",
        None,
    ),
    "lignite_coal_plant": (
        "Lignite fired power plants",
        "Supercritical steam turbine",
        None,
    ),
    "lignite_coal_plant_CCS": (
        "Lignite fired power plants",
        "Supercritical steam turbine",
        None,
    ),
    "nuclear": ("Nuclear power plants", "Nuclear III", None),
    "biomass_plant": (
        "Biomass and waste fired power plants",
        "Fluidized bed combustion",
        None,
    ),
    "biomass_plant_CCS": (
        "Biomass and waste fired power plants",
        "Fluidized bed combustion",
        None,
    ),
    # Potencia has no separate waste-fired category -- the source `Type` itself is
    # "Biomass and
    # waste fired power plants" with a single set of `Technology` rows covering both, so
    # waste_plant and biomass_plant resolve to identical Potencia figures. This is a
    # genuine
    # source-data granularity limit, not a mislabeling (unlike DEA's oil_boiler_DH/
    # waste_boiler_DH mixup, which is not reproduced in this database).
    "waste_plant": (
        "Biomass and waste fired power plants",
        "Fluidized bed combustion",
        None,
    ),
    "oil_plant": (
        "Fuel oil fired power plants",
        "Integrated gasification combined cycle",
        None,
    ),
    "fuel_cell": ("Fuel cells", "Hydrogen fuel cell power plant", None),
}

# `tech_proj` block header label (the row where the "Type:" column == "Type") -> our
# variable
# name, for the three cost-variable blocks. Other block labels present in the raw file
# ("Own
# consumption", "Technical availability (%)", "Desired range of operation - ...") aren't
# needed.
_COST_VAR_LABELS: dict[str, str] = {
    "Capital costs  €2010/kW gross": "capex",
    "Fix O&M costs  €2010/kW gross": "fopex",
    "Variable O&M  costs €2010/MWh gross": "vopex",
}
_EFFICIENCY_LABEL = "Efficiency"
_SCHEMA_UNITS: dict[str, str] = {
    "capex": "Euro/kW",
    "fopex": "Euro/kW",
    "vopex": "Euro/MWh",
}
_SRC_UNITS: dict[str, str] = {
    "capex": "€2010/kW gross",
    "fopex": "€2010/kW gross",
    "vopex": "€2010/MWh gross",
}
_MONEY_YEAR_SRC = 2010
_START_YEAR = 2010
_END_YEAR = 2050


def _cogen(technology: str) -> str:
    return "Electricity only with CCS" if "CCS" in technology else "Electricity only"


class Potencia(Dataset[pd.DataFrame]):
    """POTEnCIA (EU JRC) Central 2018 scenario technology cost and performance
    projections.

    Unlike every other agency in this database, Potencia reports a single point estimate
    per
    technology/year rather than a min/ref/max spread; every row here uses
    `scenario="ref"`.
    Also unlike the other agencies, cost/efficiency figures for a given technology are
    given at
    up to four plant sizes (XS/S/M/L) in one repeating multi-block sheet layout, of
    which S/M/L
    are used here.
    """

    name = "potencia"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "POTEnCIA Central scenario 2018 - technology cost and performance "
                "projections"
            ),
            author=["European Commission Joint Research Centre"],
            publication="European Commission, JRC POTEnCIA model",
            publication_year=2018,
            url="https://ec.europa.eu/jrc/potencia",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "cost" / "potencia"

    def _set_data(self) -> pd.DataFrame:
        cost_blocks, efficiency_block = self._read_tech_proj_blocks()
        lifetime, construction_time, availability = self._read_tech_base()

        rows: list[tuple] = []
        for technology, (potencia_type, potencia_tech, fixed_size) in _TECHS.items():
            cogen = _cogen(technology)
            for plant_size in ("S", "M", "L"):
                size = fixed_size if fixed_size is not None else plant_size
                key = (potencia_type, potencia_tech, cogen, size)
                rows += self._rows_for(
                    technology,
                    plant_size,
                    key,
                    cost_blocks,
                    efficiency_block,
                    lifetime,
                    construction_time,
                    availability,
                )

        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        data = data.drop_duplicates(subset=INDEX_NAMES)
        return data.set_index(INDEX_NAMES).sort_index()

    @staticmethod
    def _rows_for(
        technology: str,
        plant_size: str,
        key: tuple[str, str, str, str],
        cost_blocks: dict[str, pd.DataFrame],
        efficiency_block: pd.DataFrame,
        lifetime: pd.Series,
        construction_time: pd.Series,
        availability: pd.Series,
    ) -> list[tuple]:
        rows: list[tuple] = []
        for variable, block in cost_blocks.items():
            if key not in block.index:
                continue
            for year, value_src in cast(pd.Series, block.loc[key, :]).items():
                if pd.isna(value_src):
                    continue
                rows.append(
                    (
                        technology,
                        plant_size,
                        "ref",
                        variable,
                        int(cast(int, year)),
                        float(value_src),
                        _SCHEMA_UNITS[variable],
                        _MONEY_YEAR_SRC,
                        float(value_src),
                        _SRC_UNITS[variable],
                    )
                )
        if key in efficiency_block.index:
            for year, value_src in cast(
                pd.Series, efficiency_block.loc[key, :]
            ).items():
                if pd.isna(value_src):
                    continue
                rows.append(
                    (
                        technology,
                        plant_size,
                        "ref",
                        "efficiency",
                        int(cast(int, year)),
                        float(value_src),
                        "-",
                        None,
                        float(value_src),
                        "-",
                    )
                )
        for variable, series in (
            ("lifetime", lifetime),
            ("construction_time", construction_time),
            ("availability", availability),
        ):
            if key not in series.index:
                continue
            value_src = series.loc[key]
            if pd.isna(value_src):
                continue
            unit_str = "1"
            for year in YEARS:
                rows.append(
                    (
                        technology,
                        plant_size,
                        "ref",
                        variable,
                        year,
                        float(value_src),
                        unit_str,
                        None,
                        float(value_src),
                        unit_str,
                    )
                )
        return rows

    def _read_tech_proj_blocks(self) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
        """Parse the multi-block `tech_proj` sheet.

        Each block starts at a row where `Type:` == "Type"; that row's `Unnamed: 9`
        column
        names the block's variable, and the block's data rows run from two rows below
        (skipping
        the header row itself and the years-label row directly beneath it) until the row
        before
        the next such header. Blocks are keyed by (Type, Technology, Co-generation,
        Size), read
        from columns `Unnamed: 5`-`Unnamed: 8` (fully populated, unlike the leading
        `Type:`/
        `Technology:`/`Co-generation:`/`Size:` columns which rely on merged-cell
        blanks).
        """
        raw = pd.read_excel(
            self.path / "PG_technology_Central_2018.xlsx", sheet_name="tech_proj"
        )
        header_idx = raw.index[raw["Type:"] == "Type"]
        year_columns = {
            f"Unnamed: {9 + offset}": year
            for offset, year in enumerate(range(_START_YEAR, _END_YEAR + 1))
        }

        def _extract_block(start: int) -> pd.DataFrame:
            pos = cast(int, header_idx.get_loc(start))
            end = cast(
                int,
                header_idx[pos + 1] - 1 if pos + 1 < len(header_idx) else raw.index[-1],
            )
            block = raw.loc[start + 2 : end].copy()
            block = block.rename(
                columns={
                    "Unnamed: 5": "Type",
                    "Unnamed: 6": "Technology",
                    "Unnamed: 7": "Co-generation",
                    "Unnamed: 8": "Size",
                }
            )
            block = block.rename(columns=year_columns)
            block = block[block["Type"].notna()]
            for column in ("Type", "Technology", "Co-generation", "Size"):
                block[column] = block[column].str.strip()
            block = block.set_index(["Type", "Technology", "Co-generation", "Size"])
            year_cols = [year for year in YEARS if year in block.columns]
            return block[year_cols]

        cost_blocks: dict[str, pd.DataFrame] = {}
        efficiency_block = pd.DataFrame()
        for idx in header_idx:
            label = raw.loc[idx, "Unnamed: 9"]
            if label in _COST_VAR_LABELS:
                cost_blocks[_COST_VAR_LABELS[label]] = _extract_block(idx)
            elif label == _EFFICIENCY_LABEL:
                efficiency_block = _extract_block(idx)
        return cost_blocks, efficiency_block

    def _read_tech_base(self) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Parse the flat `tech_base` sheet for lifetime, construction time, and
        availability.

        One row per (Type, Technology, Co-generation, Size), no year breakdown -- the
        resulting
        single value is applied across every year in `YEARS` in `_rows_for`, matching
        how DIW's
        single-figure lifetime data is handled.
        """
        raw = pd.read_excel(
            self.path / "PG_technology_Central_2018.xlsx", sheet_name="tech_base"
        )
        for column in ("Type", "Technology", "Co-generation", "Size"):
            raw[column] = raw[column].str.strip()
        raw = raw.set_index(["Type", "Technology", "Co-generation", "Size"])
        return (
            raw["Technical lifetime (years)"],
            raw["Construction time"],
            raw["Technical availability (%)"],
        )

    # -------- methods ------------------------

    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized Potencia cost/tech data (see
        `_cost_schema`)."""
        return self.data.copy()

    def get_max_load(self, element: Technology) -> Attribute:
        """Return the technical availability."""
        availability = self.data.loc[element.name].xs("availability", level="variable")
        availability = availability["value"]
        unique_availability = availability.unique()
        if len(unique_availability) > 1:
            logging.warning(
                f"Multiple availability values found for {element.name}: "
                f"{unique_availability}. Using the first one."
            )
        attr = element.max_load
        source = SourceInformation(
            description=(
                "The maximum load (technical availability) data "
                "is derived from the Potencia dataset."
            ),
            metadata=self.metadata,
        )
        attr.set_data(
            default_value=unique_availability[0],
            source=source,
        )
        return attr
