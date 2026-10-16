"""Internally consistent hydropower capacities and natural inflows."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.technology.pan_european_climate_database import (
    PanEuropeanClimateDatabase,
)
from zen_europe.datasets.datasets.technology.pecd_hydro_capacities import (
    PECDHydroCapacities,
)

if TYPE_CHECKING:
    from zen_creator import Dataset, Technology


class HydropowerExistingCapacities(DatasetCollection):
    """Provide hydropower capacities and inflows with consistent boundaries.

    The legacy PECD hydropower database supplies power and energy capacities.
    Where that database reports no run-of-river capacity despite positive PECD
    4.2 generation, the generation is reclassified as reservoir inflow.
    Open-loop pumped storage is split into pumped and reservoir shares based on
    symmetric pumping and turbining capability. PECD 4.2 supplies weather-year
    generation and inflow profiles, and the same shares are applied to its
    open-loop natural inflow.

    Attributes:
        settings: Model settings used to select the PECD weather year.
    """

    name = "hydropower_existing_capacities"

    POWER_TECHNOLOGIES = (
        "run-of-river_hydro",
        "reservoir_hydro",
        "pumped_hydro",
    )
    ENERGY_TECHNOLOGIES = ("reservoir_hydro", "pumped_hydro")
    # PECD 4.2 reports run-of-river generation for Finland and Norway, while the
    # legacy PECD capacity data assigns their hydro turbines entirely to reservoir
    # hydro. Treating these profiles as reservoir inflow keeps the generation and
    # capacity classifications consistent without inventing additional capacity.
    ROR_AS_RESERVOIR_NODES = pd.Index(["FI", "NO"])

    def __init__(self, settings: Settings, source_path: Path | str):
        """Initialize the hydropower capacity collection.

        Args:
            settings: Model settings used when loading PECD data.
            source_path: Root directory containing the source datasets.
        """
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any]]:
        """Load the capacity and climate datasets.

        Returns:
            A dictionary containing the legacy PECD capacity dataset and PECD
            4.2 climate dataset.

        Raises:
            ValueError: If no source-data directory was provided.
        """
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "pecd_hydro_capacities": PECDHydroCapacities(self.source_path),
            "pan_european_climate_database": PanEuropeanClimateDatabase(
                settings=self.settings,
                source_path=self.source_path,
            ),
        }

    def get_capacity_existing(self, element: Technology) -> Attribute:
        """Get existing power capacity from the legacy PECD database.

        Args:
            element: Hydropower technology requesting existing power capacity.

        Returns:
            The element's existing-capacity attribute in GW.

        Raises:
            AssertionError: If the requested technology is not supported.
        """
        assert (
            element.name in self.POWER_TECHNOLOGIES
        ), f"Power capacity for {element.name} is not available in this collection."
        capacities = cast(PECDHydroCapacities, self.data["pecd_hydro_capacities"])
        return capacities.get_capacity_existing(element, power=True)

    def get_max_load_ror_hydro(self, element: Technology) -> Attribute:
        """Get ROR maximum load from PECD generation and finalized capacity."""
        pecd = cast(
            PanEuropeanClimateDatabase,
            self.data["pan_european_climate_database"],
        )
        reclassified_nodes = self.ROR_AS_RESERVOIR_NODES.intersection(
            element.model.config.system.set_nodes
        )
        generation = pecd.get_generation_run_of_river_hydro(element)
        generation = generation.drop(columns=reclassified_nodes, errors="ignore")
        capacity_data = cast(pd.Series, element.capacity_existing.df)
        capacity = capacity_data.groupby(level="node").sum()
        nodes_with_generation = generation.columns[generation.fillna(0).gt(0).any()]
        nodes_without_capacity = nodes_with_generation.difference(capacity.index)
        if not nodes_without_capacity.empty:
            raise ValueError(
                "Run-of-river capacity is missing for nodes with PECD generation: "
                f"{', '.join(nodes_without_capacity)}."
            )

        common_nodes = generation.columns.intersection(capacity.index)
        max_load = generation[common_nodes].divide(capacity.loc[common_nodes], axis=1)
        expected_nodes = set(element.model.config.system.set_nodes).difference(
            reclassified_nodes
        )
        missing_nodes = expected_nodes.difference(max_load.columns)
        if missing_nodes:
            logging.warning(
                "No matching PECD run-of-river generation and capacity for nodes: %s",
                sorted(missing_nodes),
            )

        clipped_nodes = max_load.columns[(max_load > 1).any()]
        peak_load_factors = max_load[clipped_nodes].max()
        if clipped_nodes.empty:
            clipping_description = "No countries required max-load clipping."
        else:
            clipping_details = ", ".join(
                f"{node} ({peak_load_factors[node]:.6g})" for node in clipped_nodes
            )
            logging.warning(
                "Run-of-river peak generation-to-capacity ratios exceed 1 for: %s. "
                "Clipping max-load values to 1.",
                clipping_details,
            )
            max_load = max_load.clip(upper=1)
            clipping_description = (
                "Max-load values above 1 were clipped for the following countries "
                f"(peak ratio in parentheses): {clipping_details}."
            )

        max_load.index.name = "time"
        if reclassified_nodes.empty:
            reclassification_description = (
                "No countries were reclassified as reservoir hydro."
            )
        else:
            reclassification_description = (
                "Run-of-river generation was instead added to reservoir inflow "
                "for countries without legacy run-of-river capacity: "
                f"{', '.join(reclassified_nodes)}."
            )
        source = SourceInformation(
            description=(
                "Maximum load data for run-of-river hydro is derived from PECD "
                "run-of-river and run-of-river-with-pondage generation divided by "
                "existing run-of-river capacity. "
                f"{reclassification_description} "
                f"{clipping_description}"
            ),
            metadata=pecd.metadata,
        )
        return element.max_load.set_data(source=source, df=max_load, unit="1")

    def get_capacity_existing_energy(self, element: Technology) -> Attribute:
        """Get existing energy capacity from the legacy PECD database.

        Args:
            element: Reservoir or pumped-hydro technology requesting energy
                capacity.

        Returns:
            The PECD existing-energy-capacity attribute in GWh.

        Raises:
            AssertionError: If the technology has no energy capacity.
        """
        assert element.name in self.ENERGY_TECHNOLOGIES, (
            "Existing energy capacity is only defined for reservoir_hydro and "
            f"pumped_hydro, not {element.name}."
        )
        capacities = cast(PECDHydroCapacities, self.data["pecd_hydro_capacities"])
        return capacities.get_capacity_existing(element, power=False)

    def get_flow_storage_inflow(self, element: Technology) -> Attribute:
        """Get PECD 4.2 inflow using the legacy open-loop allocation.

        Pure reservoir inflow is assigned to reservoir hydro. Open-loop pumped
        storage inflow is divided between pumped and reservoir hydro with the
        same country-level fractions used for its power and energy capacities.

        Args:
            element: Reservoir or pumped-hydro technology requesting inflow.

        Returns:
            The element's hourly natural inflow in GW.
        """
        assert element.name in self.ENERGY_TECHNOLOGIES, (
            "Storage inflow is only defined for reservoir_hydro and pumped_hydro, "
            f"not {element.name}."
        )
        capacities = cast(PECDHydroCapacities, self.data["pecd_hydro_capacities"])
        pecd = cast(
            PanEuropeanClimateDatabase,
            self.data["pan_european_climate_database"],
        )
        shares = capacities.get_open_loop_shares()
        open_loop = pecd.data["pumped_hydro"]
        missing_share_nodes = open_loop.columns.difference(shares.index)
        missing_share_nodes = missing_share_nodes[
            open_loop[missing_share_nodes].abs().sum(axis=0) > 0
        ]
        if len(missing_share_nodes) > 0:
            logging.warning(
                "Ignoring PECD 4.2 open-loop inflow for nodes without a legacy "
                "PECD capacity allocation: %s",
                list(missing_share_nodes),
            )
        fraction = shares[element.name].reindex(open_loop.columns, fill_value=0)
        data = open_loop.mul(fraction, axis=1)
        reclassified_nodes = pd.Index([])
        if element.name == "reservoir_hydro":
            data = pecd.data["reservoir_hydro"].add(data, fill_value=0)
            reclassified_nodes = self.ROR_AS_RESERVOIR_NODES.intersection(
                element.model.config.system.set_nodes
            )
            ror_energy = pecd.data["run-of-river_hydro"].add(
                pecd.data["run-of-river_with_pondage_hydro"], fill_value=0
            )
            data = data.add(
                ror_energy.reindex(columns=reclassified_nodes, fill_value=0),
                fill_value=0,
            )

        capacity = cast(pd.Series, element.capacity_existing.df)
        capacity_nodes = capacity.index.get_level_values("node").unique()
        common_nodes = data.columns.intersection(capacity_nodes)
        missing_inflow_nodes = capacity_nodes.difference(data.columns)
        if len(missing_inflow_nodes) > 0:
            logging.warning(
                "No PECD 4.2 %s inflow series for nodes with legacy capacity: %s",
                element.name,
                list(missing_inflow_nodes),
            )
        data = pecd.convert_weekly_energy_to_hourly_flow(data[common_nodes])
        if reclassified_nodes.empty:
            reclassification_description = (
                "No run-of-river energy was reclassified as reservoir inflow."
            )
        else:
            reclassification_description = (
                "Run-of-river and pondage energy was added to reservoir inflow "
                "for countries without legacy run-of-river capacity: "
                f"{', '.join(reclassified_nodes)}."
            )
        source = SourceInformation(
            description=(
                f"The natural inflow of {element.name} uses PECD 4.2. Open-loop "
                "pumped-storage inflow is allocated with the same legacy PECD "
                "fractions as its power and energy capacities. Weekly energy is "
                "converted to an hourly profile, with the final weekly rate "
                "extended over the remaining 24 hours of the year. "
                f"{reclassification_description}"
            ),
            metadata=pecd.metadata,
        )
        return element.flow_storage_inflow.set_data(
            source=source,
            df=data,
            default_value=0,
            unit="GW",
        )
