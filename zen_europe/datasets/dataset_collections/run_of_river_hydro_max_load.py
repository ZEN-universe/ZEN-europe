from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, cast

from zen_europe.datasets.dataset_collections.hydro_existing_capacity import (
    HydroExistingCapacity,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Technology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.entsoe import ENTSOE
from zen_europe.datasets.datasets.technology.pan_european_climate_database import (
    PanEuropeanClimateDatabase,
)


class RunOfRiverHydroMaxLoad(DatasetCollection):
    """Extracting maximum load data for run-of-river hydro technologies."""

    name = "run_of_river_hydro_max_load"

    ENTSOE_PSR_ROR = "B11"

    def __init__(
        self, settings: Settings, source_path: Path | str, set_nodes: list[str]
    ):
        self.settings = settings
        self.set_nodes = set_nodes
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "pan_european_climate_database": PanEuropeanClimateDatabase(
                settings=self.settings, source_path=self.source_path
            ),
            "entsoe": ENTSOE(
                settings=self.settings,
                source_path=self.source_path,
                set_nodes=self.set_nodes,
            ),
            "hydro_existing_capacity": HydroExistingCapacity(
                settings=self.settings,
                set_nodes=self.set_nodes,
                source_path=self.source_path,
            ),
        }

    def get_max_load(self, element: Technology) -> Attribute:
        """
        Get the maximum load for run-of-river hydro technologies.

        While RoR capacity reports vary a lot between datasets, we obtain
        generation and capacity from ENTSOE to ensure consistency. Note that the
        existing capacities are not necessarily the same as the ENTSOE capacity.

        """
        entsoe_dataset = cast(ENTSOE, self.data["entsoe"])
        pecd_dataset = cast(
            PanEuropeanClimateDatabase, self.data["pan_european_climate_database"]
        )
        year = element.settings.time.year_time_series
        last_entsoe_year = entsoe_dataset.last_entsoe_year
        if year > last_entsoe_year:
            logging.info(
                f"Year {year} is after the last available ENTSO-E year "
                f"{last_entsoe_year}. Using {last_entsoe_year} instead."
            )
            year = last_entsoe_year
        generation = entsoe_dataset.get_generation(
            psr_type=self.ENTSOE_PSR_ROR, year=year
        )
        generation = generation.loc[:, (generation != 0).any(axis=0)]
        generation_pecd = pecd_dataset.get_outflow_run_of_river_hydro(element)
        capacity = entsoe_dataset.get_capacity_existing(
            psr_type=self.ENTSOE_PSR_ROR, year=year
        )
        capacity = capacity.droplevel(1)
        missing_nodes_gen = set(element.model.config.system.set_nodes).difference(
            generation.columns
        )
        add_nodes_pecd = generation_pecd.columns.intersection(list(missing_nodes_gen))
        generation[add_nodes_pecd] = generation_pecd[add_nodes_pecd]
        common_nodes = generation.columns.intersection(capacity.index)
        max_load = generation[common_nodes].divide(capacity.loc[common_nodes], axis=1)
        missing_nodes = set(element.model.config.system.set_nodes).difference(
            max_load.columns
        )

        # sorted, so that the appended columns keep a stable order on disk
        for node in sorted(missing_nodes):
            if node == "SE":
                max_load[node] = max_load["NO"]
            elif node == "DK":
                max_load[node] = max_load["NL"]
            else:
                raise ValueError(
                    f"Missing node {node} in max load data for run-of-river hydro."
                )

        country_above_1 = max_load.columns[(max_load > 1).any()]
        max_load[country_above_1] = generation[country_above_1] / generation[
            country_above_1
        ].max(axis=0)

        max_load.index.name = "time"
        source = SourceInformation(
            description=(
                "Maximum load data for run-of-river hydro technologies is derived from "
                "the generation and capacity data from the ENTSOE Transparency "
                f"Platform for {year}. If available, the Pan-European Climate Database "
                f"is used to fill in missing nodes.  For {', '.join(missing_nodes)}, "
                "the maximum load is estimated based on other countries. For "
                f"{', '.join(country_above_1)}, the maximum load is above 1; "
                "therefore, the maximum load is normalized to 1 based on the maximum "
                "generation."
            ),
            metadata=self.metadata,
        )
        return element.max_load.set_data(
            source=source,
            df=max_load,
            unit="1",
        )
