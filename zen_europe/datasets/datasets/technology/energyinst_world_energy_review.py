from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    convert_country_names,
    format_capacity_existing,
)


class EnergyInstituteWorldEnergyReview(Dataset[dict[str, pd.DataFrame]]):
    """
    Dataset class to calculate the capacity limit for carbon storage based on the
    extraction of oil and gas. The idea is that the injection capacity of CO2 storage
    is limited by the amount of oil and gas that has been extracted, as the storage
    sites are often located in depleted oil and gas fields. The dataset uses the
    Energy Institute's data on oil and gas extraction to estimate the potential CO2
    storage capacity in Europe.

    """

    name = "energy_institute_world_energy_review"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Energy Institute Statistical Review of World Energy"),
            author=["Energy Institute"],
            publication="Energy Institute",
            publication_year=2023,
            url="https://www.energyinst.org/statistical-review",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path)
            / "02-carrier"
            / "energy_institute"
            / "Statistical Review of World Energy Data.xlsx"
        )

    def _set_data(self) -> dict[str, pd.DataFrame]:
        """
        The data is extracted from the IOGP CO2 storage projects database,
        which is a CSV file containing information about
        existing carbon storage projects in Europe.

        We allocate all icelandic storage projects to Norway,
        as we don't have a separate country in the model for Iceland.
        """
        oil_extr = pd.read_excel(
            self.path, sheet_name="Oil Production - Tonnes", header=2
        )
        gas_extr = pd.read_excel(self.path, sheet_name="Gas Production - EJ", header=2)
        gas_refining = pd.read_excel(
            self.path, sheet_name="Oil - Refinery capacity", header=2
        )
        oil_extr["Country"] = convert_country_names(oil_extr["Million tonnes"])
        oil_extr = oil_extr[oil_extr["Country"].notnull()].set_index("Country")

        gas_extr["Country"] = convert_country_names(gas_extr["Exajoules"])
        gas_extr = gas_extr[gas_extr["Country"].notnull()].set_index("Country")

        gas_refining["Country"] = convert_country_names(
            gas_refining["Thousand barrels daily*"]
        )
        gas_refining = gas_refining[gas_refining["Country"].notnull()].set_index(
            "Country"
        )

        # only keep columns that can be converted to int
        oil_extr = oil_extr[[c for c in oil_extr.columns if isinstance(c, int)]]
        gas_extr = gas_extr[[c for c in gas_extr.columns if isinstance(c, int)]]
        gas_refining = gas_refining[
            [c for c in gas_refining.columns if isinstance(c, int)]
        ]
        data: dict[str, pd.DataFrame] = {}
        data["oil_extraction"] = oil_extr
        data["gas_extraction"] = gas_extr
        data["gas_refining"] = gas_refining
        return data

    # -------- methods ------------------------
    def get_capacity_limit_carbon_storage(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Returns the limit on carbon storage capacity from oil and gas production.
        """
        attr = element.capacity_limit
        oil_extr = self.data["oil_extraction"]
        gas_extr = self.data["gas_extraction"]
        # convert oil from Million tonnes to bt
        oil_extr = oil_extr / Constants.DENSITY_OIL
        # convert gas from EJ to bt
        gas_extr = (
            gas_extr / Constants.NATURAL_GAS_EJ_PER_BKG / Constants.DENSITY_NATURAL_GAS
        )
        # common years
        common_years = oil_extr.columns.intersection(gas_extr.columns)
        oil_extr = oil_extr[common_years]
        gas_extr = gas_extr[common_years]
        extr = gas_extr.add(oil_extr, fill_value=0) * Constants.DENSITY_CO2
        # to ktCO2eq/hour
        extr /= Constants.HOURS_PER_YEAR / 1000
        data = extr.iloc[:, -1]

        data.name = "capacity_limit"
        data.index.name = "node"
        return attr.set_data(
            default_value=0,
            df=data,
            unit="ktCO2/h",
            source=SourceInformation(
                description=(
                    "The limit on carbon storage capacity is based on historic "
                    "oil and gas production data. The idea is that the injection "
                    "capacity of CO2 storage is limited by the amount of oil and gas "
                    "that has been extracted, as the storage sites are often located "
                    "in depleted oil and gas fields. The dataset uses the "
                    "Energy Institute's data on oil and gas extraction to "
                    "estimate the potential CO2 storage capacity in Europe."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing_refining(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Returns the existing refining capacity in Europe.

        Args:
            element (ConversionTechnology): The refining technology element.
        """
        refining_capacity = self.data["gas_refining"]
        # convert from thousand barrels daily to GW
        conversion_tb_daily_to_GW = (
            1
            / Constants.BARREL_PER_TON
            / Constants.TOE_PER_MWH
            / Constants.HOURS_PER_DAY
        )
        refining_capacity = refining_capacity * conversion_tb_daily_to_GW
        addition = calculate_capacity_addition_from_cumulative(
            refining_capacity, element=element
        )
        data = format_capacity_existing(addition)
        attr = element.capacity_existing
        attr.set_data(
            default_value=0,
            df=data,
            unit="GW",
            source=SourceInformation(
                description=(
                    "The existing refining capacity in Europe is based on the "
                    "Energy Institute's data on oil refining capacity. The dataset "
                    "provides information on the existing refining capacity in "
                    "Europe, which is used to set the existing capacity of the "
                    "refining technology element."
                ),
                metadata=self.metadata,
            ),
        )
        return attr
