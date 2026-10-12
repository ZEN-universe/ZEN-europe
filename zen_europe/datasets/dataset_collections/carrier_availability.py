from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import Attribute, Carrier, DatasetCollection, Element
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.swiss_energy_balance import (
    SwissEnergyBalance,
    SwissOilBalance,
)
from zen_europe.datasets.datasets.technology.shipping_technologies_korberg import (
    ShippingTechnologiesKorberg,
)
from zen_europe.utils.constants import Constants


class CarrierAvailability(DatasetCollection):
    """Extracting carrier availability data."""

    name = "carrier_availability"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "eurostat": Eurostat(settings=self.settings, source_path=self.source_path),
            "swiss_energy_balance": SwissEnergyBalance(source_path=self.source_path),
            "swiss_oil_balance": SwissOilBalance(source_path=self.source_path),
            "shipping_technologies_korberg": ShippingTechnologiesKorberg(
                source_path=self.source_path
            ),
        }

    def get_coal_availability(self, element: Carrier) -> Attribute:
        """
        Get the availability for coal.

        This function retrieves the coal availability data for the specified element.
        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        swiss_energy_balance_dataset = cast(
            SwissEnergyBalance, self.data["swiss_energy_balance"]
        )
        data = eurostat_dataset.get_coal_availability()
        data = data[element.name]
        assert not data.empty, "Coal availability data from Eurostat is empty."
        common_countries = data.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            data.index
        )

        data = data.loc[common_countries]

        for country in missing_countries:
            if country == "CH":
                if element.name == "hard_coal":
                    data.loc[country] = (
                        swiss_energy_balance_dataset.get_coal_availability(
                            year=eurostat_dataset.eurostat_year, element=element
                        )
                    )
                else:
                    data.loc[country] = 0.0
            else:
                raise ValueError(
                    f"Coal availability data for country {country} is not available in "
                    "the Eurostat dataset or any of the manual datasets. Please "
                    "provide the necessary data for this country."
                )

        data = data.sort_index() / Constants.HOURS_PER_YEAR  # from GWh/year to GW

        data.index.name = "node"
        data.name = "availability_import"

        source = SourceInformation(
            description=(
                "Coal availability data is derived from the Eurostat dataset, which "
                "provides availability data for various energy carriers. Additional "
                "manual data for missing countries (only CH) is obtained from the "
                "following datasets: Swiss Energy Balance dataset"
            ),
            metadata=self.metadata,
        )
        return element.availability_import.set_data(
            source=source,
            df=data,
            unit="GW",
        )

    def get_waste_availability(
        self, element: Carrier, include_industry: bool = False
    ) -> Attribute:
        """
        Get the availability for waste.

        This function retrieves the waste availability data for the specified element.
        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        swiss_energy_balance_dataset = cast(
            SwissEnergyBalance, self.data["swiss_energy_balance"]
        )
        data = eurostat_dataset.get_waste_availability(
            include_industry=include_industry
        )
        assert not data.empty, "Waste availability data from Eurostat is empty."
        common_countries = data.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            data.index
        )

        data = data.loc[common_countries]

        for country in missing_countries:
            if country == "CH":
                data.loc[country] = swiss_energy_balance_dataset.get_waste_availability(
                    year=eurostat_dataset.eurostat_year,
                    element=element,
                    include_industry=include_industry,
                )
            else:
                raise ValueError(
                    f"Waste availability data for country {country} is not available "
                    "in the Eurostat dataset or any of the manual datasets. Please "
                    "provide the necessary data for this country."
                )

        data = data.sort_index() / Constants.HOURS_PER_YEAR  # from GWh/year to GW

        data.index.name = "node"
        data.name = "availability_import"

        source = SourceInformation(
            description=(
                "Waste availability data is derived from the Eurostat dataset, which "
                "provides availability data for various energy carriers. Additional "
                "manual data for missing countries (only CH) is obtained from the "
                "following datasets: Swiss Energy Balance dataset"
            ),
            metadata=self.metadata,
        )
        return element.availability_import.set_data(
            source=source,
            df=data,
            unit="GW",
        )

    def get_oil_availability(self, element: Carrier) -> Attribute:
        """
        Get the availability for oil.

        This function retrieves the oil availability data for the specified element.
        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        swiss_energy_balance_dataset = cast(
            SwissEnergyBalance, self.data["swiss_energy_balance"]
        )
        data = eurostat_dataset.get_oil_availability()
        assert not data.empty, "Oil availability data from Eurostat is empty."
        common_countries = data.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            data.index
        )

        data = data.loc[common_countries]

        for country in missing_countries:
            if country == "CH":
                data.loc[country] = swiss_energy_balance_dataset.get_oil_availability(
                    year=eurostat_dataset.eurostat_year, element=element
                )
            else:
                raise ValueError(
                    f"Oil availability data for country {country} is not available in "
                    "the Eurostat dataset or any of the manual datasets. Please "
                    "provide the necessary data for this country."
                )

        data = data.sort_index() / Constants.HOURS_PER_YEAR  # from GWh/year to GW

        data.index.name = "node"
        data.name = "availability_import"

        source = SourceInformation(
            description=(
                "Oil availability data is derived from the Eurostat dataset, which "
                "provides availability data for various energy carriers. Additional "
                "data for missing countries (only CH) is obtained from the following "
                "datasets: Swiss Energy Balance dataset"
            ),
            metadata=self.metadata,
        )
        return element.availability_import.set_data(
            source=source,
            df=data,
            unit="GW",
        )

    def get_raw_kerosene_demand(self, element: Element) -> pd.DataFrame:
        """
        Get the demand for kerosene.

        This function retrieves the kerosene demand data for the specified element.
        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        swiss_oil_balance_dataset = cast(
            SwissOilBalance, self.data["swiss_oil_balance"]
        )
        data = eurostat_dataset.get_kerosene_demand()
        assert not data.empty, "Kerosene demand data from Eurostat is empty."
        common_countries = data.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            data.index
        )

        data = data.loc[common_countries]

        for country in missing_countries:
            if country == "CH":
                data.loc[country] = swiss_oil_balance_dataset.get_kerosene_demand(
                    year=eurostat_dataset.eurostat_year
                )
            else:
                raise ValueError(
                    f"Kerosene demand data for country {country} is not available in "
                    "the Eurostat dataset or any of the manual datasets. Please "
                    "provide the necessary data for this country."
                )

        data = data.sort_index() / Constants.HOURS_PER_YEAR  # from GWh/year to GW

        data.index.name = "node"
        data.name = "demand"
        return data

    def get_kerosene_demand(self, element: Carrier) -> Attribute:
        """
        Get the demand for kerosene.
        This function retrieves the kerosene demand data for the specified element and
        returns it as an Attribute object.
        """
        data = self.get_raw_kerosene_demand(element)
        source = SourceInformation(
            description=(
                "Kerosene demand data is derived from the Eurostat dataset. "
                "Additional data for missing countries (only CH) is obtained from the "
                "Swiss Oil Balance dataset."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=data,
            unit="GW",
        )

    def get_shipping_demand(self, element: Carrier) -> Attribute:
        """
        Get the demand for shipping.

        This function retrieves the shipping demand data for the specified element.
        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        shipping_technologies_korberg_dataset = cast(
            ShippingTechnologiesKorberg, self.data["shipping_technologies_korberg"]
        )
        data = eurostat_dataset.get_shipping_fuel_demand()
        assert not data.empty, "Shipping fuel demand data from Eurostat is empty."
        common_countries = data.index.intersection(
            element.model.config.system.set_nodes
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            data.index
        )

        data = data.loc[common_countries]

        for country in missing_countries:
            if country == "CH":
                data.loc[country] = 0.0  # assume no shipping demand in Switzerland
            else:
                raise ValueError(
                    f"Shipping fuel demand data for country {country} is not available "
                    "in the Eurostat dataset or any of the manual datasets. Please "
                    "provide the necessary data for this country."
                )

        data = data.sort_index() / Constants.HOURS_PER_YEAR  # from GWh/year to GW
        diesel2shipping = (
            shipping_technologies_korberg_dataset.get_shipping_conversion_factors(
                "diesel_ICE_ship"
            )["diesel"]
        )

        data = data / diesel2shipping
        data.index.name = "node"
        data.name = "demand"

        source = SourceInformation(
            description=(
                "Shipping fuel demand data is derived from the Eurostat dataset. "
                "For CH it is assumed that there is no shipping demand, "
                "as Switzerland is a landlocked country."
                " The demand is converted to shipping fuel demand "
                "using conversion factors from the Korberg et al. (2021) paper, "
                "which provides conversion factors for various shipping technologies."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=data,
            unit="GW",
        )
