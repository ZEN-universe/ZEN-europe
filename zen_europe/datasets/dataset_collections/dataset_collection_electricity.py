from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import os

import pandas as pd

from zen_creator.datasets.dataset_collections.dataset_collection import (
    DatasetCollection,
)


class DatasetCollectionElectricity(DatasetCollection):
    """Combined dataset for electricity-related data."""

    name = "dataset_collection_electricity"

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
        # self.model.datasets["combined_datasets_electricity"].get_electricity_demand()
        # # Carrier.get_by_name("heat").demand
        # self.model.datasets[
        #     "combined_dataset_technology"
        # ].calculate_heating_technology_share()
        raise NotImplementedError(
            "Method to calculate electricity demand based on heat demand and "
            "heating technology share is not implemented yet."
        )
