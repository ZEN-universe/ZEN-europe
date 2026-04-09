from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import os
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from entsoe import EntsoeRawClient
from entsoe.mappings import Area, lookup_area
from entsoe.parsers import parse_loads
from tqdm import tqdm

from zen_creator.datasets.datasets.dataset import Dataset


class ENTSOEAPI(Dataset):
    """Dataset class for ENTSOE data."""

    name = "entsoe_api"

    def __init__(self):
        super().__init__(name="entsoe_api")
        self.entsoe_client = EntsoeRawClient(
            api_key=self.model.config.data_source_settings.entsoe_api_key
        )

    # ------ Metadata properties ------
    @property
    def author(self) -> str:
        return "ENTSOE"

    @property
    def publication_year(self) -> int:
        return 2025

    @property
    def url(self) -> str:
        return "https://transparency.entsoe.eu/"

    # ----- Methods to get data -----

    def get_electricity_demand(self):
        if not os.path.exists(
            self.model.source_path
            / "08-processed_files"
            / "entsoe"
            / "demand_electricity_entsoe.feather"
        ):
            nodes = self.model.energy_system.set_nodes["node"]
            area_names = [area.name for area in Area]

            results_dict = {}
            print(f"Starting multiprocessing download for {len(nodes)} nodes...")
            with ProcessPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(
                        self.fetch_node_demand, node, self.entsoe_client, area_names
                    ): node
                    for node in nodes
                }

                for future in tqdm(
                    as_completed(futures), total=len(nodes), desc="Downloading"
                ):
                    node_name, series = future.result()
                    if series is not None:
                        results_dict[node_name] = series.squeeze()
                    else:
                        print(f"No data found for {node_name}")

            entsoe_demand = pd.concat(results_dict, axis=1)
            entsoe_demand = entsoe_demand.reindex(self.time_range_ts)
            if not os.path.exists(
                self.model.source_path / "08-processed_files" / "entsoe"
            ):
                os.makedirs(self.model.source_path / "08-processed_files" / "entsoe")
            entsoe_demand.to_feather(
                self.model.source_path
                / "08-processed_files"
                / "entsoe"
                / "demand_electricity_entsoe.feather"
            )
        else:
            entsoe_demand = pd.read_feather(
                self.model.source_path
                / "08-processed_files"
                / "entsoe"
                / "demand_electricity_entsoe.feather"
            )
        entsoe_demand[entsoe_demand == 0] = np.nan
        entsoe_demand = entsoe_demand.interpolate()
        entsoe_demand = entsoe_demand.fillna(0)
        entsoe_demand = entsoe_demand / 1000  # convert from MW to GW
        entsoe_demand = entsoe_demand.reset_index(drop=True)
        entsoe_demand.index.name = "time"
        return entsoe_demand

    def fetch_node_demand(self, node, client, area_names):
        """
        Worker function to fetch data for a single node.
        Returns a tuple: (node_name, demand_series) or (node_name, None) if failed.
        """
        if node == "EL":
            node_entsoe = "GR"
        else:
            node_entsoe = node

        if node_entsoe not in area_names:
            return node, None

        try:
            area = lookup_area(node_entsoe)
        except Exception:
            return node, None

        try:
            text = client.query_load(
                country_code=area, start=self.time_start_ts, end=self.time_end_ts
            )
        except Exception:
            try:
                text = client.query_load_forecast(
                    country_code=area, start=self.time_start_ts, end=self.time_end_ts
                )
            except Exception:
                return node, None

        try:
            demand_data = parse_loads(text, process_type="A16")
            demand_data = demand_data.tz_convert(area.tz)
            demand_data = demand_data.truncate(
                before=self.time_start_ts, after=self.time_end_ts
            )
            demand_data = demand_data.resample("h").mean()
            return node, demand_data
        except Exception:
            return node, None
