from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Carrier, ConversionTechnology, Dataset


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.utils.constants import Constants


class OlefinDemand(DatasetCollection):
    """Extracting olefin demand data."""

    name = "olefin_demand"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "aidres": Aidres(self.source_path),
            "eurostat": Eurostat(source_path=self.source_path, settings=self.settings),
        }

    def get_olefin_demand(self, element: Carrier) -> Attribute:
        """
        Get the demand for olefin.

        The idea is to use the naphtha demand from Eurostat as a proxy for olefin
        demand,
        since naphtha is a key feedstock for olefin production.
        The function retrieves the naphtha demand data
         and processes it to obtain the olefin demand.
        """
        aidres_dataset = cast(Aidres, self.data["aidres"])
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        eurostat_data = eurostat_dataset.get_naphtha_demand()
        common_countries = eurostat_data.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            eurostat_data.index
        )
        d = eurostat_data.loc[common_countries, eurostat_dataset.eurostat_year]
        for country in missing_countries:
            if country == "CH":
                d.loc[country] = 0  # no olefin demand in Switzerland
            else:
                raise ValueError(f"Missing olefin demand data for country {country}.")
        d = d / Constants.HOURS_PER_YEAR  # convert from GWh/a to GWh/h

        naphtha2olefin = aidres_dataset.get_conversion_factors_aidres(
            "olefin_from_naphtha"
        )["naphtha"]

        d = d / naphtha2olefin  # [GWh/h/[GWh/t]] = [t/h]

        d.index.name = "node"
        d.name = "demand"

        source = SourceInformation(
            description=(
                "Olefin demand derived from naphtha demand from Eurostat, "
                "with conversion factors from the Aidres dataset."
                "The naphtha demand is used as a proxy for olefin demand, "
                "since naphtha is a key feedstock for olefin production."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=d,
            unit="tproduct/h",
        )

    def get_capacity_existing_olefin(self, element: ConversionTechnology) -> Attribute:
        """
        Get the existing olefin production capacity.

        We assume that currently all olefin production is based on naphtha.

        Args:
            element (ConversionTechnology): The element for which to get the
                existing capacity.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        eurostat_data = eurostat_dataset.get_naphtha_demand()
        eurostat_data = (
            eurostat_data / Constants.HOURS_PER_YEAR
        )  # convert from GWh/a to GWh/h

        cf = cast(
            list[dict[str, dict[str, Any]]], element.conversion_factor.default_value
        )
        cf_n = next((item for item in cf if "naphtha" in item), None)
        if cf_n is None:
            raise ValueError(
                "Conversion factor for naphtha not found in the conversion factor list."
            )

        naphtha2olefin = cf_n["naphtha"]["default_value"]

        olefin_demand = eurostat_data / naphtha2olefin  # [GWh/h/[GWh/t]] = [t/h]

        capacity_addition = calculate_capacity_addition_from_cumulative(
            olefin_demand, element
        )
        existing_capacity = format_capacity_existing(capacity_addition)
        common_nodes = existing_capacity.index.get_level_values(0).intersection(
            element.model.config.system.set_nodes
        )
        existing_capacity = existing_capacity.loc[common_nodes]
        source = SourceInformation(
            description=(
                "Existing olefin production capacity derived from the naphtha demand "
                "data. We assume that currently all olefin production is based on "
                "naphtha."
            ),
            metadata=self.metadata,
        )
        attr = element.capacity_existing
        attr.set_data(
            default_value=0,
            df=existing_capacity,
            unit="tproduct/h",
            source=source,
        )
        return attr
