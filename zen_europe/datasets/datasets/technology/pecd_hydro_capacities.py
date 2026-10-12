from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator import Technology

from zen_creator import Attribute
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation


class PECDHydroCapacities(Dataset[pd.DataFrame]):
    """
    Installed hydropower capacities of the ENTSO-E Pan-European Climate Database.

    Machine-readable conversion of the hydropower modelling data that ENTSO-E
    publishes alongside the PECD. The turbining capacity (MW) and the reservoir
    capacity (GWh) are reported per ENTSO-E market zone and aggregated to NUTS0
    nodes here.

    The PECD plant types are mapped to run-of-river, reservoir and pumped hydro.
    Closed loop pumped storage is pumped hydro, while open loop pumped storage is
    split between pumped and reservoir hydro, see `_split_open_loop`.
    """

    name = "pecd_hydro_capacities"

    URL = (
        "https://zenodo.org/records/3985078/files/"
        "PECD-hydro-capacities.csv?download=1"
    )

    VARIABLE_MAPPING = {
        "Total turbining capacity (MW)": "power",
        "Total pumping capacity (MW)": "power_pumping",
        "Reservoir capacity (GWh)": "energy",
        "Reservoir capacity linked to Run of River and Pondage units (GWh)": "energy",
        "Cumulated (upper or head) reservoir capacity (GWh)": "energy",
    }

    # market zone prefixes that differ from the NUTS0 node code
    NODE_MAPPING = {"GR": "EL"}

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="ENTSO-E Hydropower modelling data (PECD) in CSV format",
            author=["Matteo De Felice"],
            publication="Zenodo",
            publication_year=2020,
            url="https://zenodo.org/records/3985078",
            doi="https://doi.org/10.5281/zenodo.3985078",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "capacity_existing"

    def _set_data(self) -> pd.DataFrame:
        file_path = self.path / "PECD-hydro-capacities.csv"
        if not file_path.exists():
            logging.info(f"Downloading {self.name} from {self.URL}...")
            pd.read_csv(self.URL).to_csv(file_path, index=False)
        data = pd.read_csv(file_path)
        data["node"] = data["zone"].str[:2].replace(self.NODE_MAPPING)
        data["variable"] = data["variable"].map(self.VARIABLE_MAPPING)

        capacities = data.pivot_table(
            index=["type", "node"],
            columns="variable",
            values="value",
            aggfunc="sum",
        ).fillna(0)
        capacities["power"] = capacities["power"] / 1000
        capacities["power_pumping"] = capacities["power_pumping"].abs() / 1000

        pumped_open, reservoir_open = self._split_open_loop(
            capacities.loc["Pump Storage - Open Loop"]
        )
        data_agg = pd.concat(
            [
                capacities.loc["Run-of-River and pondage"],
                capacities.loc["Reservoir"].add(reservoir_open, fill_value=0),
                capacities.loc["Pump Storage - Closed Loop"].add(
                    pumped_open, fill_value=0
                ),
            ],
            keys=["run-of-river_hydro", "reservoir_hydro", "pumped_hydro"],
            names=["technology", "node"],
        )
        return data_agg[["power", "energy"]].rename(
            columns={
                "power": "capacity_existing",
                "energy": "capacity_existing_energy",
            }
        )

    @staticmethod
    def _split_open_loop(open_loop: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split open loop pumped storage into a pumped and a reservoir hydro share.

        The pumped share is min(pumping, turbining)/max(pumping, turbining), so
        plants that pump back about as much as they turbine count as pumped hydro,
        while reservoirs with little pumping capacity count as reservoir hydro.
        The latter applies to Norway, whose entire fleet is reported as open loop
        pumped storage although it barely pumps.

        Returns:
            tuple: The pumped hydro and the reservoir hydro share.
        """
        capacities = open_loop[["power", "power_pumping"]]
        share = (capacities.min(axis=1) / capacities.max(axis=1)).fillna(0)
        return open_loop.mul(share, axis=0), open_loop.mul(1 - share, axis=0)

    # -------- methods ------------------------
    def get_capacity_existing(self, element: Technology, power: bool) -> Attribute:
        """
        Get the existing capacity for a hydro technology.

        Args:
            element: The element for which to get the existing capacity.
            power: If True, returns the power capacity; if False, the energy capacity.

        Returns:
            Attribute: The existing capacity attribute of the element.
        """
        assert element.name in self.data.index.get_level_values("technology"), (
            f"Existing capacity data for {element.name} is not available in the "
            "PECD hydro capacities dataset."
        )
        if power:
            data = self.data.loc[element.name, "capacity_existing"]
            attr = element.capacity_existing
            unit = "GW"
        else:
            data = self.data.loc[element.name, "capacity_existing_energy"]
            attr = element.capacity_existing_energy
            unit = "GWh"

        set_nodes = element.model.config.system.set_nodes
        data = data[data.index.isin(set_nodes)]
        data = data[data > 0]
        year_construction = element.settings.time.reference_year - 1
        data = pd.concat({year_construction: data}, names=["year_construction"])
        data = data.swaplevel(0, 1).sort_index()

        source = SourceInformation(
            description=(
                f"The existing capacity of {element.name} is derived from the "
                "hydropower modelling data of the Pan-European Climate Database, "
                "aggregated from the ENTSO-E market zones to the nodes."
            ),
            metadata=self.metadata,
        )
        return attr.set_data(
            df=data,
            source=source,
            unit=unit,
        )
