from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.datasets.datasets.carrier.when2heat import When2Heat

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import Attribute, Carrier, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.dataset_collections.heat_demand import HeatDemand
from zen_europe.datasets.datasets.carrier.bfe import BFE
from zen_europe.datasets.datasets.carrier.entsoe import ENTSOE
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat


class ElectricityDemand(DatasetCollection):
    """Extracting electricity demand data."""

    name = "electricity_demand"

    def __init__(
        self, settings: Settings, set_nodes: list[str], source_path: Path | str
    ):
        self.settings = settings
        self.set_nodes = set_nodes
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "entsoe": ENTSOE(self.settings, self.set_nodes, self.source_path),
            "heat_demand": HeatDemand(self.settings, self.source_path),
            "eurostat": Eurostat(self.settings, self.source_path),
            "when2heat": When2Heat(self.settings, self.source_path),
            "bfe": BFE(self.source_path),
        }

    @staticmethod
    def _validate_heating_share_year(
        requested_year: int,
        heating_share_hp: pd.DataFrame,
        heating_share_eb: pd.DataFrame,
    ) -> None:
        """Raise a descriptive error if heating-share data lacks a requested year."""
        missing_from = []
        if requested_year not in heating_share_hp.columns:
            missing_from.append("heat-pump data")
        if requested_year not in heating_share_eb.columns:
            missing_from.append("electrode-boiler data")
        if not missing_from:
            return

        heat_pump_years = sorted(heating_share_hp.columns, key=str)
        electrode_boiler_years = sorted(heating_share_eb.columns, key=str)
        raise ValueError(
            f"Heating-share year {requested_year} is missing from "
            f"{' and '.join(missing_from)}. Available heat-pump years: "
            f"{heat_pump_years}. Available electrode-boiler years: "
            f"{electrode_boiler_years}."
        )

    def get_demand(self, element: Carrier) -> Attribute:
        """
        Get the electricity demand for the specified element.

        """
        # get base demand data from ENTSOE dataset
        demand = self._get_base_demand()
        # load heat demand
        heat_demand_dataset = cast(HeatDemand, self.data["heat_demand"])
        heat_demand = heat_demand_dataset._calculate_demand(element)
        # load heating share, ignores district heating electricity demand
        heating_share = heat_demand_dataset._calculate_heating_share_household()
        heating_share_hp = cast(pd.DataFrame, heating_share.loc["heat_pump"])
        heating_share_eb = cast(pd.DataFrame, heating_share.loc["electrode_boiler"])
        common_nodes = heating_share_hp.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_nodes = set(element.model.config.system.set_nodes).difference(
            common_nodes
        )
        assert len(missing_nodes) == 0, (
            f"Missing nodes in heating share data: " f"{missing_nodes}"
        )
        time_series_year = self.settings.time.time_series_year
        self._validate_heating_share_year(
            time_series_year, heating_share_hp, heating_share_eb
        )
        heating_share_hp = heating_share_hp.loc[common_nodes, time_series_year]
        heating_share_eb = heating_share_eb.loc[common_nodes, time_series_year]
        heat_demand_hp = heat_demand * heating_share_hp
        heat_demand_eb = heat_demand * heating_share_eb
        electricity_demand_eb = (
            heat_demand_eb * 1
        )  # assume 100% efficiency for electrode boilers
        when2heat_dataset = cast(When2Heat, self.data["when2heat"])
        cop_data = when2heat_dataset.get_COP()
        cop_data = cast(pd.DataFrame, cop_data.xs("floor", level="category", axis=1))
        electricity_demand_hp = heat_demand_hp.div(cop_data, axis=0)
        # correct demand
        demand = demand - electricity_demand_eb - electricity_demand_hp
        demand = demand.clip(lower=0)  # ensure no negative demand
        source = SourceInformation(
            description=(
                "The electricity demand data is derived from multiple sources:"
                "First, the ENTSOE dataset provides the base electricity demand data. "
                "Second, the electricity demand must be corrected for the"
                "electricity demand of heat pumps and electrode boilers. "
                "The heat demand data is derived from the HeatDemand dataset, "
                "which combines data from the JRC IDEES, Eurostat, "
                "DESNZ, BFE, and Energifaktanorge datasets. "
                "The heating share data by technology is derived "
                "from the HeatDemand dataset, especially from Eurostat. "
                "Finally, the COP data for heat pumps is derived "
                "from the When2Heat dataset."
                "Note that we neglect the embedded electricity demand for district "
                "heating, which is assumed to be small."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=demand,
            unit="GW",
        )

    def _get_base_demand(self) -> pd.DataFrame:
        """
        Get the base electricity demand data.

        Returns:
            pd.DataFrame: A DataFrame containing the base electricity demand data.
        """
        entsoe_dataset = cast(ENTSOE, self.data["entsoe"])
        return entsoe_dataset.get_demand()
