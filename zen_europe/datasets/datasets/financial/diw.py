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

# internal technology name -> DIW cost-sheet technology label. DIW only
# reports a single (reference) capex figure per technology, no fopex/vopex.
_COST_TECHS: dict[str, str] = {
    "wind_onshore": "OnshoreWind",
    "wind_offshore_near_shore": "OffshoreWind[shallow]",
    "wind_offshore": "OffshoreWind[transitional]",
    "photovoltaics": "PVUtility",
    "rooftop_photovoltaics": "PVRooftop[residential]",
    "rooftop_photovoltaics_com": "PVRooftop[commercial]",
    "run-of-river_hydro": "Hydro[small]",
    "reservoir_hydro": "Hydro[large]",
    "natural_gas_turbine": "GasPowerPlant(CCGT)",
    "natural_gas_turbine_CCS": "GasPowerPlant(CCGT)+CCTS",
    "hard_coal_plant": "HardCoalPowerPlant",
    "hard_coal_plant_CCS": "HardCoalPowerPlant+CCTS",
    "lignite_coal_plant": "LignitePowerPlant",
    "lignite_coal_plant_CCS": "LignitePowerPlant+CCTS",
    "nuclear": "NuclearPowerPlant",
    "biomass_plant": "BiomassPowerPlant",
    "biomass_plant_CCS": "BiomassPowerPlant+CCTS",
    "oil_plant": "OilPowerPlant(CCGT)",
    "fuel_cell": "FuelCell",
}
# efficiency sheet uses yet another label set, only covering thermal plants
_EFFICIENCY_TECHS: dict[str, str] = {
    "natural_gas_turbine": "CCGT(NaturalGas)",
    "hard_coal_plant": "HardCoal",
    "lignite_coal_plant": "Lignite",
    "nuclear": "Nuclear",
    "oil_plant": "CCGT(Oil)",
}
# lifetime sheet uses a third label set
_LIFETIME_TECHS: dict[str, str] = {
    "wind_onshore": "OnshoreWind",
    "wind_offshore_near_shore": "OffshoreWind",
    "wind_offshore": "OffshoreWind",
    "photovoltaics": "PVUtility",
    "rooftop_photovoltaics": "PVRooftop",
    "rooftop_photovoltaics_com": "PVRooftop",
    "run-of-river_hydro": "HydroPowerPlant",
    "reservoir_hydro": "HydroPowerPlant",
    "natural_gas_turbine": "GasPowerPlant(CCGT)",
    "natural_gas_turbine_CCS": "GasPowerPlant(CCGT)",
    "hard_coal_plant": "HardCoalPowerPlant",
    "hard_coal_plant_CCS": "HardCoalPowerPlant",
    "lignite_coal_plant": "LignitePowerPlant",
    "lignite_coal_plant_CCS": "LignitePowerPlant",
    "nuclear": "NuclearPowerPlant",
    "biomass_plant": "BiomassPowerPlant",
    "biomass_plant_CCS": "BiomassPowerPlant",
    "oil_plant": "OilPowerPlant(CCGT)",
}
_MONEY_YEAR_SRC = 2018
# The "costs" sheet is numerically in kEuro/MW, which equals Euro/kW 1:1.
_SOURCE_CAPEX_UNIT = "kEuro/MW"


class DIW(Dataset[pd.DataFrame]):
    """DIW (German Institute for Economic Research) 2018 power-plant cost data.

    This class implements the specific behavior for the DIW dataset.
    """

    name = "diw"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Current and Prospective Costs of Electricity Generation until 2050",
            author=["Wolf-Peter Schill", "Alexander Zerrahn", "Fabian Kunz"],
            publication="DIW Data Documentation 94",
            publication_year=2018,
            url="https://www.diw.de/documents/publikationen/73/diw_01.c.573921.de/diwkompakt_2018-128.pdf",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "cost" / "diw"

    def _set_data(self) -> pd.DataFrame:
        path = self.path / "capex_diw.xlsx"
        costs = pd.read_excel(path, header=1, sheet_name="costs").set_index(
            "Technology"
        )
        costs.columns = costs.columns.astype(int)
        efficiency = pd.read_excel(path, header=1, sheet_name="efficiency").set_index(
            "Efficiency"
        )
        efficiency.columns = efficiency.columns.astype(int)
        lifetime = pd.read_excel(path, sheet_name="lifetime").set_index("Column1")[
            "Column2"
        ]

        rows = []
        for technology, diw_tech in _COST_TECHS.items():
            if diw_tech not in costs.index:
                continue
            for year, value_src in costs.loc[diw_tech].items():
                if pd.isna(value_src):
                    continue
                rows.append(
                    (
                        technology,
                        "M",
                        "ref",
                        "capex",
                        int(year),
                        float(value_src),
                        "Euro/kW",
                        _MONEY_YEAR_SRC,
                        float(value_src),
                        _SOURCE_CAPEX_UNIT,
                    )
                )
        for technology, diw_tech in _EFFICIENCY_TECHS.items():
            if diw_tech not in efficiency.index:
                continue
            for year, value_src in efficiency.loc[diw_tech].items():
                if pd.isna(value_src):
                    continue
                rows.append(
                    (
                        technology,
                        "M",
                        "ref",
                        "efficiency",
                        int(year),
                        float(value_src),
                        "-",
                        None,
                        float(value_src),
                        "-",
                    )
                )
        for technology, diw_tech in _LIFETIME_TECHS.items():
            if diw_tech not in lifetime.index:
                continue
            value_src = lifetime.loc[diw_tech]
            if pd.isna(value_src):
                continue
            # DIW gives one lifetime figure per technology, applied to the whole year
            # grid
            for year in costs.columns:
                rows.append(
                    (
                        technology,
                        "M",
                        "ref",
                        "lifetime",
                        int(year),
                        float(value_src),
                        "1",
                        None,
                        float(value_src),
                        "years",
                    )
                )
        data = pd.DataFrame(rows, columns=INDEX_NAMES + VALUE_COLUMNS)
        return data.set_index(INDEX_NAMES).sort_index()

    # -------- methods ------------------------

    def get_costs(self) -> pd.DataFrame:
        """Return the parsed, standardized DIW cost/tech data (see `_cost_schema`)."""
        return self.data.copy()
