from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd
from zen_creator import (
    Attribute,
    ConversionTechnology,
    RetrofittingTechnology,
    SourceInformation,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import convert_country_names, format_capacity_existing

MAPPING_CCS = {
    "Hard to abate industry (cement plant)": "cement_post_comb",
    "Fuel Production (Biofuels)": "biomass_plant_CCS",
    "Fuel Production (Oil & Gas)": "natural_gas_turbine_CCS",
    "Fuel Production (Biogas)": "natural_gas_turbine_CCS",
    "Fuel Production (Hydrogen)": "SMR_CCS",
    "Hard to abate industry (Chemicals)": "SMR_CCS",
    "Direct Air Capture": "DAC",
    "Power Production (Geothermal)": "biomass_plant_CCS",
    "Upstream Oil & Gas (Gas Processing)": "natural_gas_turbine_CCS",
}
MAPPING_INDUSTRIAL_CLUSTERS = {
    "Ravenna CCS (includes Callisto)": [
        "natural_gas_turbine_CCS",
        "SMR_CCS",
        "cement_post_comb",
        "BF_BOF_CCS",
    ],
    "Longship (includes Northern Lights 1)": [
        "cement_post_comb",
    ],
    "Viking CCS": ["natural_gas_turbine_CCS"],  # Immingham Power Station
    "HyNet North West": ["SMR_CCS"],
    "Net Zero Teesside": ["natural_gas_turbine_CCS"],
}


class IOGPCarbonStorageProjects(Dataset[pd.DataFrame]):
    """
    Dataset class for the existing carbon storage projects based on the IOGP
    (International Oil & Gas Producers Association) report.

    """

    name = "IOGP_carbon_storage_projects"

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("CO2 storage projects in Europe"),
            author=["IOGP"],
            publication="IOGP",
            publication_year=2026,
            url="https://iogpeurope.org/carbon-capture-use-storage-feb2023/",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path)
            / "03-technology"
            / "capacity_existing"
            / "carbon_storage"
            / "co2_storage_projects_europe.csv"
        )

    def _set_data(self) -> pd.DataFrame:
        """
        The data is extracted from the IOGP CO2 storage projects map,
        which is a CSV file containing information about
        existing carbon storage projects in Europe.

        We allocate all icelandic storage projects to Norway,
        as we don't have a separate country in the model for Iceland.
        """
        data = pd.read_csv(self.path)
        data["country"] = data["country"].replace({"Iceland": "Norway"})
        data["project"] = data["node"]
        data["node"] = convert_country_names(data["country"])
        data = data[data["year_construction"] != "no data"]
        data = data.set_index(["node", "year_construction"])

        return data

    # -------- methods ------------------------
    def get_capacity_existing_data(self) -> pd.DataFrame:
        """
        Returns the existing carbon storage capacity data from the IOGP report.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the existing carbon storage
                capacity data.
        """
        data = self.data.copy()
        if not self.settings.investment.consider_carbon_storage_expansion:
            data = data[data["entry_type"] != "expansion"]
            data = data[data["status"].isin(["In operation", "FID"])]
        data = data["co2_storage_injection_capacity_mtpa"]
        data = data / Constants.HOURS_PER_YEAR * 1e6  # convert from Mtpa to tCO2/h
        data.index = data.index.set_levels(
            data.index.levels[data.index.names.index("year_construction")].astype(int),
            level="year_construction",
        )
        return data

    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """
        Returns the existing carbon storage capacity from the IOGP report.
        """
        data = self.get_capacity_existing_data()
        if not self.settings.investment.set_future_CCS_investments:
            reference_year = self.settings.time.reference_year
            data = data[
                data.index.get_level_values("year_construction") <= reference_year - 1
            ]
        data = format_capacity_existing(data)
        attr = element.capacity_existing
        return attr.set_data(
            default_value=0,
            df=data,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The existing carbon storage capacity is based on the IOGP report "
                    "'CO2 Storage Projects in Europe'."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing_capture(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """
        Returns the existing carbon capture capacity from the IOGP report.

        For industrial clusters, the capture capacity is split among the different
        technologies based on the mapping defined in MAPPING_INDUSTRIAL_CLUSTERS.
        """
        attr = element.capacity_existing
        data = self.data[self.data["is_capture"]]
        data = data[data.index.get_level_values("year_construction") != "no data"]
        data.index = data.index.remove_unused_levels()
        data.index = data.index.set_levels(
            data.index.levels[data.index.names.index("year_construction")].astype(int),
            level="year_construction",
        )
        data = data.sort_index()
        data.loc[:, "type_capture_project"] = data["type_capture_project"].map(
            MAPPING_CCS
        )
        for idx, row in data[data["type_capture_project"].isna()].iterrows():
            project = re.sub(r" - Expansion( \d+)?", "", row["project"])
            if project in MAPPING_INDUSTRIAL_CLUSTERS:
                mi = pd.MultiIndex.from_tuples([idx], names=data.index.names)
                for tech in MAPPING_INDUSTRIAL_CLUSTERS[project]:
                    ser = row.copy()
                    ser["type_capture_project"] = tech
                    ser["co2_storage_injection_capacity_mtpa"] = row[
                        "co2_storage_injection_capacity_mtpa"
                    ] / len(MAPPING_INDUSTRIAL_CLUSTERS[project])
                    data = pd.concat([data, pd.DataFrame([ser], index=mi)])
            else:
                logging.warning(
                    f"Project {project} not found in MAPPING_INDUSTRIAL_CLUSTERS. "
                    "This project will be ignored in the existing capture capacity "
                    "calculation."
                )

        data = data[data["type_capture_project"].notna()]
        data = data.rename(columns={"type_capture_project": "technology"})
        data = data.set_index("technology", append=True)
        if element.name not in data.index.get_level_values("technology"):
            raise ValueError(
                f"Technology {element.name} not found in the existing capture capacity "
                "data. Please check the MAPPING_CCS and MAPPING_INDUSTRIAL_CLUSTERS "
                "dictionaries."
            )
        data_tech = data.xs(element.name, level="technology")
        data_tech = data_tech["co2_storage_injection_capacity_mtpa"]
        data_tech = (
            data_tech / Constants.HOURS_PER_YEAR * 1e6
        )  # convert from Mtpa to tCO2/h
        if not element.settings.investment.set_future_CCS_investments:
            reference_year = element.settings.time.reference_year
            data_tech = data_tech[
                data_tech.index.get_level_values("year_construction") <= reference_year
            ]
        data_tech = format_capacity_existing(data_tech)
        return attr.set_data(
            default_value=0,
            df=data_tech,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The existing carbon capture capacity is based on the IOGP report "
                    "'CO2 Storage Projects in Europe'. "
                    "For industrial clusters, the capture capacity is split among the "
                    "different technologies based on the mapping defined in "
                    "MAPPING_INDUSTRIAL_CLUSTERS."
                ),
                metadata=self.metadata,
            ),
        )
