from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

import eurostat
import pandas as pd

from zen_creator.datasets.datasets.dataset import Dataset


class EurostatApi(Dataset):
    """Dataset class for Eurostat data."""

    name = "eurostat"

    def __init__(self, model: Model):
        super().__init__(name="eurostat", model=model)
        self.eurostat_start_year = 1990

    # ------ Metadata properties ------
    @property
    def author(self) -> str:
        return "Eurostat"

    @property
    def publication_year(self) -> int:
        return 2025

    @property
    def url(self) -> str:
        return "https://ec.europa.eu/eurostat"

    # ----- Methods to get data -----
    def get_eurostat_data(
        self,
        nrg_bal,
        siec,
        geo=None,
        start_period=None,
        dataset="nrg_bal_c",
        unit="GWH",
    ):
        """queries the eurostat api."""
        filter_pars = {"start_period": self.data_general_year}
        filter_pars["unit"] = unit
        # start_period
        if start_period is not None:
            filter_pars["start_period"] = start_period
        # geo
        eurostat_countries = eurostat.get_par_values(dataset, "geo")
        if geo is None:
            geo = self.model.energy_system.set_nodes["node"].to_list()
        geo = set(geo)
        common_geo = list(geo.intersection(eurostat_countries))
        assert (
            len(common_geo) > 0
        ), f"None of the locations {geo} are in Eurostat database"
        filter_pars["geo"] = common_geo
        # siec
        common_siec = list(
            set(eurostat.get_par_values(dataset, "siec")).intersection(siec)
        )
        assert len(common_siec) > 0, f"None of the siec {siec} are in Eurostat database"
        filter_pars["siec"] = common_siec
        # nrg_bal
        common_bal = list(
            set(eurostat.get_par_values(dataset, "nrg_bal")).intersection(nrg_bal)
        )
        assert (
            len(common_bal) > 0
        ), f"None of the nrg_bal {nrg_bal} are in Eurostat database"
        filter_pars["nrg_bal"] = common_bal
        filter_pars_comp = [(filter_pars, g, dataset) for g in common_geo]

        eurostat_result = []

        # for i in filter_pars_comp:
        #     eurostat_result.append(self.extract_single_data_eurostat(i))
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_geo = {
                executor.submit(self.extract_single_data_eurostat, item): item
                for item in filter_pars_comp
            }

            for future in as_completed(future_to_geo):
                try:
                    data = future.result()
                    eurostat_result.append(data)
                except Exception as exc:
                    item = future_to_geo[future]
                    print(f"Eurostat query failed for {item}: {exc}")

        return pd.concat(eurostat_result)

    def extract_single_data_eurostat(self, args):
        """this extracts the value for a geo datapoint."""
        filter_pars = copy.copy(args[0])
        geo = args[1]
        dataset = args[2]
        filter_pars["geo"] = geo
        extract_bal = eurostat.get_data_df(dataset, filter_pars=filter_pars)
        return extract_bal

    def get_eurostat_heat(self):
        """get eurostat heat data."""
        siec = {
            "C0000X0350-0370": "Solid fossil fuels",
            "P1000": "Peat and peat products",
            "O4000XBIO": "Oil and petroleum products",
            "G3000": "Natural gas",
            "R5110-5150_W6000RI": "Primary solid biofuels",
            "R5300": "Biogases",
            "E7000": "Electricity",
            "RA600": "Ambient heat",
            "H8000": "Heat",
            "W6100_6220": "Non-renewable waste",
            "C0350-0370": "Manufactured gases",
            "N900H": "Nuclear heat",
        }
        nrg_bal = {
            "GHP": "Gross heat production",
            "FC_OTH_E": "Final consumption - other sectors - energy use",
        }
        # rename techs:
        tech_names = {
            "Solid fossil fuels": "hard_coal_boiler",
            "Peat and peat products": "hard_coal_boiler",
            "Oil and petroleum products": "oil_boiler",
            "Natural gas": "natural_gas_boiler",
            "Primary solid biofuels": "biomass_boiler",
            "Biogases": "biomass_boiler",
            "Electricity": "electrode_boiler",
            "Ambient heat": "heat_pump",
            "Heat": "heat",
            "Non-renewable waste": "waste_boiler",
            "Manufactured gases": "natural_gas_boiler",
            "Nuclear heat": "hard_coal_boiler",
        }
        tech_names_DH = {
            "Solid fossil fuels": "hard_coal_boiler_DH",
            "Peat and peat products": "hard_coal_boiler_DH",
            "Oil and petroleum products": "oil_boiler_DH",
            "Natural gas": "natural_gas_boiler_DH",
            "Primary solid biofuels": "biomass_boiler_DH",
            "Biogases": "biomass_boiler_DH",
            "Electricity": "electrode_boiler_DH",
            "Ambient heat": "heat_pump_DH",
            "Heat": "heat",
            "Non-renewable waste": "waste_boiler_DH",
            "Manufactured gases": "natural_gas_boiler_DH",
            "Nuclear heat": "hard_coal_boiler_DH",
        }
        # get electricity use in households
        siec_HH = ["E7000"]
        nrgbal_HH = ["FC_OTH_HH_E", "FC_OTH_HH_E_LE", "FC_OTH_HH_E_CK"]
        dataset_HH = "nrg_d_hhq"
        unit_HH = "TJ"
        start_period = self.eurostat_start_year
        # TODO figure out what is wrong with the data hint:
        # ["FC_OTH_HH_E", "FC_OTH_HH_E_LE", "FC_OTH_HH_E_CK"] for PL are
        # missing completely (=0)
        if not os.path.exists(
            self.model.source_path
            / "08-processed_files"
            / "eurostat"
            / "eurostat_heat.feather"
        ):
            eurostat_electricity_HH = self.get_eurostat_data(
                nrg_bal=nrgbal_HH,
                siec=siec_HH,
                dataset=dataset_HH,
                unit=unit_HH,
                start_period=start_period,
            )  # usage of electricity in households
            eurostat_heat = self.get_eurostat_data(
                nrg_bal, siec, start_period=start_period
            )
            eurostat = {"heat": eurostat_heat, "ele_HH": eurostat_electricity_HH}
            df_heat = pd.concat(eurostat)
            if not os.path.exists(
                self.model.source_path / "08-processed_files" / "eurostat"
            ):
                os.makedirs(self.model.source_path / "08-processed_files" / "eurostat")
            df_heat.to_feather(
                self.model.source_path
                / "08-processed_files"
                / "eurostat"
                / "eurostat_heat.feather"
            )
        else:
            df_heat = pd.read_feather(
                self.model.source_path
                / "08-processed_files"
                / "eurostat"
                / "eurostat_heat.feather"
            )

        # limit to eurostat year
        df_heat = (
            df_heat.drop(["freq", "unit"], axis=1)
            .set_index(["nrg_bal", "geo\\TIME_PERIOD", "siec"])
            .squeeze()
        )
        df_heat = df_heat.loc[
            :, df_heat.columns.astype(int) <= self.data_general_year
        ].astype(float)
        heat_index = df_heat.index
        df_heat_int = df_heat.reset_index(drop=True).bfill(
            axis=1
        )  # .interpolate(axis=1)
        df_heat_int.index = heat_index
        df_heat = df_heat_int
        # ffill because UK has missing values at the end
        df_heat = df_heat.ffill(axis=1)
        return df_heat, siec, tech_names, tech_names_DH
