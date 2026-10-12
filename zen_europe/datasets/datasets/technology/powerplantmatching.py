from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from zen_creator import Attribute, Technology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.utils.utils import convert_country_names, format_capacity_existing


class PowerPlantMatching(Dataset[pd.DataFrame]):
    """
    Power plant matching dataset class.

    """

    name = "powerplantmatching"

    ALLOWED_STATUS = [
        "Commissioned",
        "Partially commissioned",
        "Decommissioned",
        "Financing secured / under construction",
    ]

    TECHNOLOGY_MAPPING: dict[str, dict[str, list[Any]]] = {
        "lignite_coal_plant": {"Fueltype": ["Lignite"]},
        "hard_coal_plant": {
            "Fueltype": [
                "Hard Coal",
                "Anthracite",
                "Bituminous Coal",
                "Coke",
                "Coal Unknown",
            ]
        },
        "natural_gas_turbine": {"Fueltype": ["Natural Gas"]},
        "nuclear": {"Fueltype": ["Nuclear"]},
        "oil_plant": {"Fueltype": ["Oil"]},
        "waste_plant": {
            "Fueltype": ["Waste"],
        },
        "biomass_plant": {"Fueltype": ["Solid Biomass", "Biogas"]},
        "run-of-river_hydro": {"Fueltype": ["Hydro"], "Technology": ["Run-Of-River"]},
        "reservoir_hydro": {"Fueltype": ["Hydro"], "Technology": ["Reservoir"]},
        "pumped_hydro": {"Fueltype": ["Hydro"], "Technology": ["Pumped Storage"]},
        "wind_onshore": {"Fueltype": ["Wind"], "Technology": ["Onshore", np.nan]},
        "wind_offshore": {"Fueltype": ["Wind"], "Technology": ["Offshore"]},
        "photovoltaics": {"Fueltype": ["Solar"], "Technology": ["PV", np.nan]},
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    @staticmethod
    def _assign_technology(
        df: pd.DataFrame, mapping: dict[str, dict[str, list[Any]]]
    ) -> pd.Series:
        """Assign each row of `df` the technology whose mapping criteria it matches.

        A row matches a technology if, for every column the technology's mapping
        specifies, the row's value is in that column's allowed-values list; a mapping
        that omits a column (e.g. "Fueltype" for `nuclear`) doesn't check it --
        the columns it does specify are already selective enough. Rows matching no
        technology get NaN; if a row matches more than one technology (mappings are
        expected to be mutually exclusive), the first one wins.
        """
        technology: pd.Series = pd.Series(np.nan, index=df.index, dtype="object")
        for tech, criteria in mapping.items():
            mask = pd.Series(True, index=df.index)
            for column, allowed_values in criteria.items():
                crit_mask = df[column].isin(allowed_values)
                if np.nan in allowed_values:
                    crit_mask |= df[column].isna()
                mask &= crit_mask
            technology.loc[mask & technology.isna()] = tech
        return technology

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Performing energy modelling exercises in a transparent way - The "
                "issue of data quality in power plant databases"
            ),
            author=[
                "Fabian Gotzens",
                "Heidi Heinrichs",
                "Jonas Hörsch",
                "Fabian Hofmann",
            ],
            publication="Energy Strategy Reviews",
            publication_year=2019,
            url="https://powerplantmatching.readthedocs.io/en/latest/",
            doi="https://doi.org/10.1016/j.esr.2018.11.004",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "capacity_existing"

    def _set_data(self) -> pd.DataFrame:
        if not os.path.exists(
            self.path / "processed_powerplantmatching_data_raw.feather"
        ):
            # imported here because powerplantmatching pulls in matplotlib and
            # is only needed when the processed file has not been cached yet
            import powerplantmatching as ppm

            data = ppm.powerplants(from_url=True)
            logging.info(f"Before filtering: {len(data)} power plants")
            data = data[data["DateIn"].notna()]
            data["year"] = data["DateIn"].astype(int)
            data["node"] = convert_country_names(data["Country"])
            data = data[data["node"].notna()]
            logging.info(
                f"After removing nan years and nodes: {len(data)} power plants"
            )
            data["technology"] = self._assign_technology(data, self.TECHNOLOGY_MAPPING)
            data = data[data["technology"].notna()]
            logging.info(f"After assigning technologies: {len(data)} power plants")
            data_raw = data[
                [
                    "Name",
                    "Country",
                    "Capacity",
                    "DateIn",
                    "DateRetrofit",
                    "DateOut",
                    "lat",
                    "lon",
                    "StorageCapacity_MWh",
                    "year",
                    "node",
                    "technology",
                ]
            ]
            data_raw.to_feather(
                self.path / "processed_powerplantmatching_data_raw.feather"
            )
        else:
            data = pd.read_feather(
                self.path / "processed_powerplantmatching_data_raw.feather"
            )
        return data

    # -------- methods ------------------------
    def get_capacity_existing(self, element: Technology) -> Attribute:
        """
        Get the existing capacity for a technology.

        Args:
            element: The element for which to get the existing capacity.

        Returns:
            Attribute: The existing capacity attribute of the element.
        """
        data_raw = self.data.copy()
        data_raw = data_raw[
            data_raw["DateOut"].isna()
            | (data_raw["DateOut"] > element.settings.time.reference_year)
        ]
        data = data_raw.groupby(["technology", "node", "year"])["Capacity"].sum()
        data = data.sort_index() / 1000  # convert MW to GW
        assert element.name in data.index.get_level_values(0), (
            f"Existing capacity data for {element.name} is not available in the "
            "PowerPlantMatching dataset."
        )
        data = data.loc[element.name]
        reference_year = element.settings.time.reference_year
        data = data[data.index.get_level_values("year") < reference_year]
        data = format_capacity_existing(data)
        source = SourceInformation(
            description=(
                "The existing capacity data is derived from the PowerPlantMatching "
                "dataset."
            ),
            metadata=self.metadata,
        )
        attr = element.capacity_existing.set_data(df=data, source=source, unit="GW")
        return attr

    def estimate_lifetime(self, element, threshold=0.25) -> int | None:
        """
        estimate the lifetime of a technology based on the existing capacity data.

        If less than {threshold} of the plants have been decommissioned, return None.

        Args:
            element: The element for which to estimate the lifetime.
            threshold: The minimum proportion of decommissioned plants required to
                estimate the lifetime.

        Returns:
            int: The estimated lifetime of the technology in years.
        """
        data = self.data.copy()
        assert element.name in data["technology"].unique(), (
            f"Existing capacity data for {element.name} is "
            "not available in the PowerPlantMatching dataset."
        )
        data = data[data["technology"] == element.name]
        decommissioned = data[data["DateOut"].notna()]
        if len(decommissioned) < threshold * len(data):
            return None
        age = decommissioned["DateOut"] - decommissioned["DateIn"]
        median_lifetime = int(age.median())
        return median_lifetime
