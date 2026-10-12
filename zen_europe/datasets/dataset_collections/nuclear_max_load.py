from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset

    from zen_europe.elements.conversion_technologies.nuclear import Nuclear


import calendar

from zen_creator import DatasetCollection
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.entsoe import ENTSOE


class NuclearMaxLoad(DatasetCollection):
    """Extracting maximum load data for nuclear power plants.

    This dataset collection provides information on the real-life availability of
    nuclear power plants, which is used to determine the maximum load that can be
    expected from these plants. The maximum load is calculated based on the actual
    generation data of nuclear power plants, taking into account their capacity.

    """

    name = "nuclear_max_load"

    NUM_PAST_YEARS = 4

    def __init__(
        self, settings: Settings, set_nodes: list[str], source_path: Path | str
    ):
        self.settings = settings
        self.set_nodes = set_nodes
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "entsoe": ENTSOE(
                settings=self.settings,
                set_nodes=self.set_nodes,
                source_path=self.source_path,
            ),
        }

    def get_max_load(self, element: Nuclear) -> tuple[pd.DataFrame, pd.Series]:
        """
        Calculate the maximum load for nuclear power plants based on historical
        generation data.
        The maximum load is determined by analyzing the generation data of nuclear power
        plants
        over the past NUM_PAST_YEARS years. The average maximum load is calculated for
        each node
        and for the total system.

        """
        entsoe_db = ENTSOE(
            settings=self.settings,
            set_nodes=self.set_nodes,
            source_path=self.source_path,
        )

        ref_year = element.settings.time.reference_year
        last_entsoe_year = entsoe_db.last_entsoe_year
        if ref_year > last_entsoe_year:
            logging.info(
                f"Reference year {ref_year} is after the last "
                f"available ENTSO-E year {last_entsoe_year}. "
                f"Using {last_entsoe_year} instead."
            )
            ref_year = last_entsoe_year
        years = range(ref_year - self.NUM_PAST_YEARS, ref_year + 1)
        nodal_ml_by_year = {}
        total_ml_by_year = {}
        for year in years:
            gen = entsoe_db.get_generation(element.NUCLEAR_PSR_TYPE, year=year)
            gen = gen.dropna(axis=1, how="all")
            capa = entsoe_db.get_capacity_existing(element.NUCLEAR_PSR_TYPE, year=year)
            capa = capa.droplevel("year_construction")
            common_nodes = gen.columns.intersection(capa.index)
            gen = gen.loc[:, common_nodes]
            capa = capa.loc[common_nodes]
            if calendar.isleap(year):
                # drop 29 Feb so every year aligns to the same 8760 hours
                leap_day_hours = range((31 + 28) * 24, (31 + 29) * 24)
                gen = gen.loc[~gen.index.isin(leap_day_hours)].reset_index(drop=True)
            nodal_ml_by_year[year] = gen.divide(capa, axis=1).clip(upper=1)
            total_ml_by_year[year] = (gen.sum(axis=1) / capa.sum()).clip(upper=1)
        nodal_ml_df = pd.concat(nodal_ml_by_year, axis=1).T.groupby(level=1).mean().T
        nodal_ml_df = nodal_ml_df.loc[:, ~nodal_ml_df.isna().all(axis=0)]
        total_ml_df = pd.concat(total_ml_by_year, axis=1).mean(axis=1)
        return nodal_ml_df, total_ml_df
