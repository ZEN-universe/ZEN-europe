from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import os

import pandas as pd

from zen_creator.datasets.dataset_collections.dataset_collection import (
    DatasetCollection,
)


class DatasetCollectionHeat(DatasetCollection):
    """Combined dataset for heat-related data."""

    name = "dataset_collection_heat"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    # ------ Metadata properties ------
    @property
    def author(self) -> str:
        return "-"

    @property
    def publication_year(self) -> int:
        return -1

    @property
    def url(self) -> str:
        return "-"

    # ----- Methods to get data -----
    def calculate_heating_technology_share(self):
        if not os.path.exists(
            self.model.source_path
            / "08-processed_files"
            / "heating_technologies"
            / "heating_technology_share.feather"
        ):
            # get eurostat heat data
            df_heat, siec, tech_names, tech_names_DH = self.model.datasets[
                "eurostat"
            ].get_eurostat_heat()
            # calculate heating technology share
            heating_technology_share = self.calculate_total_heat(
                df_heat, siec, tech_names, tech_names_DH
            )
            # use idees heating technology share to modify share between
            # electrode boiler and heat pump
            heating_share_idees = self.calculate_idees_heating_share()
            # adapt heating technology share
            heating_technology_share = self.adapt_heating_shares(
                heating_share_idees, heating_technology_share
            )
            if not os.path.exists(
                self.model.source_path / "08-processed_files" / "heating_technologies"
            ):
                os.makedirs(
                    self.model.source_path
                    / "08-processed_files"
                    / "heating_technologies"
                )
            heating_technology_share.to_feather(
                self.model.source_path
                / "08-processed_files"
                / "heating_technologies"
                / "heating_technology_share.feather"
            )
        else:
            heating_technology_share = pd.read_feather(
                self.model.source_path
                / "08-processed_files"
                / "heating_technologies"
                / "heating_technology_share.feather"
            )
        return heating_technology_share

    def calculate_total_heat(self, df_heat, siec, tech_names, tech_names_DH):
        """calculate total heat."""
        fin_con_tot = {}
        ghp_tot = {}
        for year in df_heat.columns:
            df_heat_year = df_heat[year].astype(float).unstack()
            df_heat_year = df_heat_year.rename(siec, axis=1)
            fin_con = df_heat_year.loc["FC_OTH_E"]
            ghp = df_heat_year.loc["GHP"]
            fin_con = fin_con.rename(tech_names, axis=1)
            fin_con = fin_con.T.groupby(level=[0]).sum(numeric_only=True).T
            ghp = ghp.rename(tech_names_DH, axis=1)
            ghp = ghp.T.groupby(level=[0]).sum(numeric_only=True).T
            eleHHTot = df_heat_year.loc["FC_OTH_HH_E", "Electricity"]  # total
            eleHHLE = df_heat_year.loc["FC_OTH_HH_E_LE", "Electricity"]  # lighting
            eleHHCK = df_heat_year.loc["FC_OTH_HH_E_CK", "Electricity"]  # cooking
            # share of ghp consumed in other sectors (not industry)
            ghp4con = (
                ghp.multiply(fin_con["heat"] / ghp.sum(axis=1), axis=0)
                .fillna(0)
                .drop("heat", axis=1)
            )
            # share of electricity not used for electrical appliances and cooking
            shareEle = 1 - (eleHHLE + eleHHCK) / eleHHTot
            common_countries = fin_con.index.intersection(shareEle.index)
            fin_con.loc[common_countries, "electrode_boiler"] *= shareEle
            # substract electricity for heat pumps from "electrode_boiler"
            if self.ds.td.cost_comp.check_if_available(
                "heat_pump", df_type="tech", variable="efficiency"
            ):
                # efficiency_HP = self.ds.td.cost_comp.get_average(
                #     df_type="tech",
                #     technology="heat_pump",
                #     variable="efficiency",
                #     metric="median",
                # )[0].iloc[0]
                efficiency_HP = self.ds.td.cop_hp.mean().mean()
                efficiency_EB = self.ds.td.cost_comp.get_average(
                    df_type="tech",
                    technology="electrode_boiler",
                    variable="efficiency",
                    metric="median",
                )[0].iloc[0]
            else:
                efficiency_HP = self.ds.td.constants.get_manual_efficiencies(
                    "heat_pump"
                )
                efficiency_EB = self.ds.td.constants.get_manual_efficiencies(
                    "electrode_boiler"
                )
            fin_con["electrode_boiler"] -= (
                fin_con["heat_pump"] / efficiency_HP * efficiency_EB
            )
            # fin_con is in quantities of input_carrier (except heat pump) -->
            # convert to output_carrier heat with efficiencies
            for tech in fin_con.columns:
                if tech != "heat" and tech != "heat_pump":
                    if self.ds.td.cost_comp.check_if_available(
                        tech, df_type="tech", variable="efficiency"
                    ):
                        efficiency = self.ds.td.cost_comp.get_average(
                            df_type="tech",
                            technology=tech,
                            variable="efficiency",
                            metric="median",
                        )[0].iloc[0]
                    else:
                        efficiency = self.ds.td.constants.get_manual_efficiencies(tech)
                    fin_con[tech] *= efficiency
            # add CH
            fin_con.loc["CH"] = fin_con.loc["AT"]
            ghp4con.loc["CH"] = ghp4con.loc["AT"]
            self.ghp4con = ghp4con
            self.fin_con = fin_con.rename({"heat": "district_heating_grid"}, axis=1)
            fin_con_tot[year] = self.fin_con
            ghp_tot[year] = self.ghp4con
        fin_con = pd.concat(fin_con_tot, keys=fin_con_tot.keys(), axis=1)
        ghp = pd.concat(ghp_tot, keys=ghp_tot.keys(), axis=1)
        efficiency_DHG = self.ds.td.constants.get_manual_efficiencies(
            "district_heating_grid"
        )
        ghp = ghp / efficiency_DHG
        total_heat = fin_con.stack().groupby(level=0).sum()
        # calculate heating share
        comb_heat = pd.concat([fin_con, ghp], axis=1).stack()
        heating_technology_share = comb_heat.div(total_heat)
        return heating_technology_share

    def get_demand(self):
        total_demand = self.model.datasets[
            "eu_building_observatory"
        ].load_total_heat_data()
        w2h_data = self.model.datasets["when2heat"].load_heat_demand_profiles()
        heat_demand = pd.DataFrame(
            index=range(8760), columns=self.model.energy_system.set_nodes["node"]
        )
        for node in total_demand.index:
            if node == "EL":
                node_W2H = "GR"
            elif node == "UK":
                node_W2H = "GB"
            else:
                node_W2H = node
            demand_ts = w2h_data.loc[:, w2h_data.columns.str.contains(node_W2H)]
            if not demand_ts.columns.empty:
                res_space = (
                    demand_ts[f"{node_W2H}_heat_profile_space_MFH"]
                    * total_demand.loc[node, "res_space"]
                    / 1000
                )
                res_water = (
                    demand_ts[f"{node_W2H}_heat_profile_water_MFH"]
                    * total_demand.loc[node, "res_water"]
                    / 1000
                )
                nores_space = (
                    demand_ts[f"{node_W2H}_heat_profile_space_COM"]
                    * total_demand.loc[node, "nores_space"]
                    / 1000
                )
                nores_water = (
                    demand_ts[f"{node_W2H}_heat_profile_water_COM"]
                    * total_demand.loc[node, "nores_water"]
                    / 1000
                )
                heat_demand[node] = (
                    res_space + res_water + nores_space + nores_water
                ).interpolate()
                assert not heat_demand[node].isna().any()
            else:
                # assume constant heat demand
                heat_demand[node] = total_demand.loc[node].sum() / 8.76
        # add missing countries
        heat_demand = self.get_heat_demand_for_missing_countries(
            heat_demand, total_demand, w2h_data
        )
        heat_demand = heat_demand.dropna(axis=1)
        common_countries = heat_demand.columns.intersection(
            self.model.energy_system.set_nodes["node"]
        )
        assert common_countries.isin(
            self.model.energy_system.set_nodes["node"]
        ).all(), "Not all heat demand countries are in the energy system nodes"
        heat_demand = heat_demand[common_countries]
        heat_demand.index.name = "time"
        return heat_demand

    def get_heat_demand_for_missing_countries(
        self, heat_demand, total_demand, w2h_data
    ):
        """get heat demand for missing countries."""
        missing_countries = heat_demand.columns[heat_demand.isna().all(axis=0)]
        additional_countries_w2h = w2h_data.columns.str[0:2].unique().drop(["ut", "ce"])
        extra_countries = additional_countries_w2h.intersection(missing_countries)
        for extra_country in extra_countries:
            manual_demand = self.get_manual_heat_demand(extra_country)
            demand_ts = w2h_data.loc[:, w2h_data.columns.str.contains(extra_country)]
            if extra_country == "CH":
                sub_country = "AT"
            elif extra_country == "NO":
                sub_country = "SE"
            else:
                continue
            tot_sub_demand = total_demand.loc[sub_country].sum()
            res_space = (
                demand_ts[f"{extra_country}_heat_profile_space_MFH"]
                * total_demand.loc[sub_country, "res_space"]
                / 1000
            )
            res_water = (
                demand_ts[f"{extra_country}_heat_profile_water_MFH"]
                * total_demand.loc[sub_country, "res_water"]
                / 1000
            )
            nores_space = (
                demand_ts[f"{extra_country}_heat_profile_space_COM"]
                * total_demand.loc[sub_country, "nores_space"]
                / 1000
            )
            nores_water = (
                demand_ts[f"{extra_country}_heat_profile_water_COM"]
                * total_demand.loc[sub_country, "nores_water"]
                / 1000
            )
            heat_demand[extra_country] = (
                (res_space + res_water + nores_space + nores_water)
                * manual_demand
                / tot_sub_demand
            ).interpolate()
            assert not heat_demand[extra_country].isna().any()
        return heat_demand

    @staticmethod
    def get_manual_heat_demand(node):
        """returns manual heat demand for nodes in TWh."""
        heat_demand = {
            "CH": 100.66,
            # source Energieperspektiven Bundesamt für Energie, Table 8
            # https://www.bfe.admin.ch/bfe/en/home/politik/
            # energieperspektiven-2050-plus.exturl.html/
            # aHR0cHM6Ly9wdWJkYi5iZmUuYWRtaW4uY2gvZGUvcHVibGljYX/
            # Rpb24vZG93bmxvYWQvMTAzMjQ=.html
            "NO": 40 * 7.1 / 4.6,
            # measured from screen, source DNV Energy Transition Norway, page 19
            # https://www.norskindustri.no/siteassets/dokumenter/
            # rapporter-og-brosjyrer/energy-transition-norway-2021.pdf
        }
        return heat_demand[node]
