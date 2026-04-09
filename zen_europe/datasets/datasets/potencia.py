from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    pass

from pathlib import Path

import numpy as np
import pandas as pd
from zen_creator.datasets.datasets.ECB import ECB

from zen_creator.datasets.techno_economic_dataset import TechnoEconomicDataset


class Potencia(TechnoEconomicDataset[Dict[str, pd.DataFrame]]):
    """Dataset class for the Potencia source data."""

    name = "potencia"

    def __init__(self, source_path: Path | str):
        self.start_year = 2010
        self.end_year = 2050
        self.vars = {
            "Capital costs  €2010/kW gross": "capex",
            "Variable O&M  costs €2010/MWh gross": "vopex",
            "Fix O&M costs  €2010/kW gross": "fopex",
        }
        super().__init__(source_path=source_path)

        self.set_available_technologies(
            finance=self.data["finance"],
            efficiency=self.data["efficiency"],
            lifetime=self.data["lifetime"],
            construction_time=self.data["construction_time"],
        )

    # ------ Metadata properties ------
    def _set_title(self) -> str:
        return "The POTEnCIA Central scenario: an EU energy outlook to 2050. "

    def _set_author(self) -> str:
        return (
            "Mantzos, L., Wiesenthal, T., Neuwahl, F. & Rózsai, M. "
            "The POTEnCIA Central scenario: an EU energy outlook to 2050. "
            "JRC Science for Policy Report 346 (2019) doi:10.2760/32835."
        )

    def _set_publication(self) -> str:
        return "JRC Science for Policy Report 346"

    def _set_publication_year(self) -> int:
        return 2019

    def _set_url(self) -> str:
        return "https://publications.jrc.ec.europa.eu/repository/handle/JRC118353"

    @property
    def money_year_source(self) -> int:
        return 2010

    @property
    def unit(self) -> str:
        return "Euro/kW"

    def _set_path(self) -> Path:
        return self.source_path / "07-techno_economic_parameters" / self.name

    # ----- Methods to get data -----
    def _set_data(self):
        """Method to load the raw techno-economic data."""
        url = self.path / "PG_technology_Central_2018.xlsx"
        raw_finance_data = pd.read_excel(url, sheet_name="tech_proj")
        raw_tech_data = pd.read_excel(url, sheet_name="tech_base").set_index(
            ["Type", "Technology", "Co-generation", "Size"]
        )

        type_idx = raw_finance_data.index[raw_finance_data["Type:"] == "Type"]
        var_idx = raw_finance_data.index[
            raw_finance_data["Unnamed: 9"].isin(list(self.vars.keys()))
        ]
        eff_idx = raw_finance_data.index[
            raw_finance_data["Unnamed: 9"].isin(["Efficiency"])
        ]
        assert var_idx.difference(
            type_idx
        ).empty, "Potencia xlsx does not look as planned"
        # efficiency data
        raw_eff_data = raw_finance_data.loc[
            eff_idx.min() : type_idx[np.argmax(type_idx > eff_idx.max())] - 1
        ]
        raw_eff_data = raw_eff_data[~raw_eff_data.isna().all(axis=1)]
        raw_eff_data.to_csv(self.source_path / "raw_eff_data.csv")
        # cost data
        raw_finance_data = raw_finance_data.loc[
            var_idx.min() : type_idx[np.argmax(type_idx > var_idx.max())] - 1
        ]
        raw_finance_data = raw_finance_data[~raw_finance_data.isna().all(axis=1)]
        raw_finance_data.to_csv(self.source_path / "raw_finance_data.csv")
        # lifetime data
        raw_lt_data = raw_tech_data["Technical lifetime (years)"]
        raw_lt_data.to_csv(self.source_path / "raw_lt_data.csv")
        # construction time data
        raw_ct_data = raw_tech_data["Construction time"]
        raw_ct_data.to_csv(self.source_path / "raw_ct_data.csv")

        raw_finance_data = raw_finance_data.reset_index(drop=True)
        raw_eff_data = raw_eff_data.reset_index(drop=True)
        raw_eff_data = raw_eff_data.loc[2:]
        raw_eff_data["Variable"] = "Efficiency"

        raw_finance_data = self._set_index_of_df(raw_finance_data)
        raw_eff_data = self._set_index_of_df(raw_eff_data)

        raw_finance_data = self._rename_finance_tech(raw_finance_data)
        raw_eff_data = self._rename_efficiency_tech(raw_eff_data)
        raw_lt_data = self._rename_lt_tech(raw_lt_data)
        raw_ct_data = self._rename_ct_tech(raw_ct_data)

        return {
            "finance": raw_finance_data,
            "efficiency": raw_eff_data,
            "lifetime": raw_lt_data,
            "construction_time": raw_ct_data,
        }

    def _set_index_of_df(self, df: pd.DataFrame) -> pd.DataFrame:
        type_idx = df.index[df["Type:"] == "Type"]
        drop_idx = type_idx.to_list()
        df["Variable"] = ""
        for idx, pos in enumerate(type_idx):
            drop_idx.append(pos + 1)
            if pos != type_idx[-1]:
                df.loc[pos : type_idx[idx + 1], "Variable"] = df.loc[pos, "Unnamed: 9"]
            else:
                df.loc[pos:, "Variable"] = df.loc[pos, "Unnamed: 9"]
        df = df.drop(index=drop_idx)
        df = df.drop(
            columns=["Unnamed: 4", "Type:", "Technology:", "Co-generation:", "Size:"]
        )
        df = df.rename(
            {
                "Unnamed: 5": "Type",
                "Unnamed: 6": "Technology",
                "Unnamed: 7": "Co-generation",
                "Unnamed: 8": "Size",
            },
            axis=1,
        )
        df = df.set_index(["Type", "Technology", "Co-generation", "Size", "Variable"])
        years = {
            f"Unnamed: {9+_idx}": _year
            for _idx, _year in enumerate(range(self.start_year, self.end_year + 1))
        }
        df = df.rename(years, axis=1)[self.get_years()]
        return df

    # def filter(self, df: pd.DataFrame, tech_df: bool = False) -> pd.DataFrame:
    #     """Method to filter the dataframe."""
    #     df_filtered = df.copy()
    #     if not tech_df:
    #         mask_capex = (
    #             df_filtered.index.get_level_values("variable").isin(["capex"])
    #         )
    #         mask_ref = df_filtered.index.get_level_values("scenario").isin(["ref"])
    #         mask_size = df_filtered.index.get_level_values("plant_size").isin(["M"])
    #         df_filtered = df_filtered.loc[mask_capex & mask_ref & mask_size]
    #     return df_filtered

    def _rename_finance_tech(self, df: pd.DataFrame) -> pd.DataFrame:
        """Method to rename finance and techno-economic parameters."""
        Potencia_names = {
            "wind_onshore": ("Wind power plants", "Onshore", "Electricity only"),
            "wind_offshore": ("Wind power plants", "Offshore", "Electricity only"),
            "photovoltaics": (
                "Solar PV power plants",
                "Solar PV power plants",
                "Electricity only",
                "L",
            ),
            "rooftop_photovoltaics": (
                "Solar PV power plants",
                "Solar PV power plants",
                "Electricity only",
                "S",
            ),
            "rooftop_photovoltaics_com": (
                "Solar PV power plants",
                "Solar PV power plants",
                "Electricity only",
                "M",
            ),
            "solar_thermal": (
                "Solar thermal power plants",
                "Solar thermal power plants",
                "Electricity only",
            ),
            "run-of-river_hydro": ("Hydro plants", "Run-of-river", "Electricity only"),
            "reservoir_hydro": (
                "Hydro plants",
                "Reservoirs (dams)",
                "Electricity only",
            ),
            "natural_gas_turbine": (
                "Gas fired power plants (Natural gas, biogas)",
                "Gas turbine combined cycle",
                "Electricity only",
            ),
            "natural_gas_turbine_CCS": (
                "Gas fired power plants (Natural gas, biogas)",
                "Gas turbine combined cycle",
                "Electricity only with CCS",
            ),
            "oc_natural_gas_turbine": (
                "Gas fired power plants (Natural gas, biogas)",
                "Gas turbine",
                "Electricity only",
            ),
            "hard_coal_plant": (
                "Coal fired power plants",
                "Supercritical steam turbine",
                "Electricity only",
            ),
            "hard_coal_plant_CCS": (
                "Coal fired power plants",
                "Supercritical steam turbine",
                "Electricity only with CCS",
            ),
            "lignite_coal_plant": (
                "Lignite fired power plants",
                "Supercritical steam turbine",
                "Electricity only",
            ),
            "lignite_coal_plant_CCS": (
                "Lignite fired power plants",
                "Supercritical steam turbine",
                "Electricity only with CCS",
            ),
            # source: # https://world-nuclear.org/information-library/
            # nuclear-fuel-cycle/nuclear-power-reactors/
            # advanced-nuclear-power-reactors.aspx
            "nuclear": (
                "Nuclear power plants",
                "Nuclear III",
                "Electricity only",
            ),
            # source: https://world-nuclear.org/information-library/
            # nuclear-fuel-cycle/nuclear-power-reactors/
            # advanced-nuclear-power-reactors.aspx
            "smr": (
                "Nuclear power plants",
                "Nuclear IV",
                "Electricity only",
            ),
            # source: https://world-nuclear.org/information-library/
            # nuclear-fuel-cycle/nuclear-power-reactors/
            # advanced-nuclear-power-reactors.aspx
            "biomass_plant": (
                "Biomass and waste fired power plants",
                "Fluidized bed combustion",
                "Electricity only",
            ),  # https://www.ieabioenergyreview.org/biomass-combustion/
            "biomass_plant_CCS": (
                "Biomass and waste fired power plants",
                "Fluidized bed combustion",
                "Electricity only with CCS",
            ),
            "waste_plant": (
                "Biomass and waste fired power plants",
                "Fluidized bed combustion",
                "Electricity only",
            ),
            # compared the largest BNEF oil plants, both Steam Engine and IGCC,
            # but modern ones are IGCC
            "oil_plant": (
                "Fuel oil fired power plants",
                "Integrated gasification combined cycle",
                "Electricity only",
            ),
            "pumped_hydro": ("Pumped storage", "Pumped storage", "Electricity only"),
            "fuel_cell": (
                "Fuel cells",
                "Hydrogen fuel cell power plant",
                "Electricity only",
            ),
        }
        df_renamed = self.rename_index(df, Potencia_names)
        if isinstance(df_renamed.index, pd.MultiIndex):
            df_renamed.index.names = ["technology"] + df_renamed.index.names[1:]
            assert (
                len(df_renamed.index.names[1:]) == 1
                and df_renamed.index.names[1] == "Variable"
            ), "Potencia finance data must have only 'Variable' as second index level"
            df_renamed.index = df_renamed.index.rename({"Variable": "variable"})
            if (df_renamed.index.get_level_values("variable") == "").all():
                df_renamed = df_renamed.droplevel("variable")
        else:
            df_renamed.index.name = "technology"
        return df_renamed

    def _rename_efficiency_tech(self, df: pd.DataFrame) -> pd.DataFrame:
        """Method to rename efficiency techno-economic parameters."""
        df_renamed = self._rename_finance_tech(df)
        return df_renamed

    def _rename_lt_tech(self, df: pd.DataFrame) -> pd.DataFrame:
        """Method to rename lifetime techno-economic parameters."""
        df_renamed = self._rename_finance_tech(df)
        return df_renamed

    def _rename_ct_tech(self, df: pd.DataFrame) -> pd.DataFrame:
        """Method to rename construction time techno-economic parameters."""
        df_renamed = self._rename_finance_tech(df)
        return df_renamed

    # ------ Public methods for retrieving data ------

    def get_cost_data(self, technology, variable, target_year):

        df_finance = self._convert_finance_data(
            self.data["finance"], target_year=target_year
        )
        df_finance.sort_index(inplace=True)
        df_tech = df_finance.loc[(technology, variable)].T
        df_tech.index.name = "year"
        df_tech.name = variable
        return df_tech.squeeze()

    def get_lifetime(self, technology):
        df_lifetime = self.data["lifetime"]
        lt = df_lifetime.loc[technology]
        if len(lt) == 1:
            df_lt = pd.Series(index=self.get_years(), data=lt.squeeze())
        else:
            df_lt = pd.DataFrame(
                index=self.get_years(),
                data=np.tile(lt.values, (len(self.get_years()), 1)),
                columns=lt.index,
            )
        df_lt.index.name = "year"
        df_lt.name = "lifetime"
        return df_lt

    def get_efficiency(self, technology):
        df_efficiency = self.data["efficiency"]
        eff = df_efficiency.loc[technology].T
        eff.index.name = "year"
        df_tech = eff.squeeze()
        return df_tech

    def get_construction_time(self, technology):
        raise NotImplementedError("Method not implemented for Potencia dataset.")
        # ct = int(df_construction_time.loc[technology].squeeze())
        # df_ct = pd.Series(index=self.get_years(), data=ct)
        # df_ct.index.name = "year"
        # df_ct.name = "construction_time"
        # return df_ct

    def _convert_finance_data(self, df: pd.DataFrame, target_year) -> pd.DataFrame:
        """Method to convert finance data to target money year and align units."""
        variables = df.index.get_level_values("variable").unique()
        assert all(var in self.vars.keys() for var in variables), (
            "Potencia finance data contains unknown variables: "
            f"{variables.difference(self.vars.keys())}"
        )
        assert (
            self.get_units("money") == "Euro"
            and self.get_units("power") == "kW"
            and self.get_units("energy") == "kWh"
        ), (
            "Potencia capex data unit conversion assumes Euro/kW and "
            "Euro/kWh as target unit"
        )
        new_index = df.index.get_level_values("variable").map(self.vars)
        df.index = pd.MultiIndex.from_arrays(
            [df.index.get_level_values("technology"), new_index],
            names=["technology", "variable"],
        )

        # convert vopex from €/MWh to €/kWh
        mask_vopex = df.index.get_level_values("variable") == "vopex"
        df.loc[mask_vopex] = df.loc[mask_vopex] / 1000

        inflation = ECB().get_inflation_rate(
            base_year=self.money_year_source, target_year=target_year
        )
        df_converted = df * inflation
        return df_converted
