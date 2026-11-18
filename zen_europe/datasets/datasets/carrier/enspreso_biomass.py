from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.carriers.carrier import Carrier

import pandas as pd
from zen_creator import Scenario
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute, SourceInformation

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import interpolate_missing_years


class EnspresoBiomass(Dataset[pd.DataFrame]):
    """Dataset class for the ENSPRESO biomass data.

    This class provides methods to extract biomass availability and price
    """

    name = "enspreso_biomass"

    def __init__(self, source_path: Path | str | None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="ENSPRESO - BIOMASS",
            author=["Joint Research Centre (JRC)"],
            publication="European Commission",
            publication_year=2019,
            url="https://data.jrc.ec.europa.eu/dataset/"
            "74ed5a04-7d74-4807-9eab-b94774309d9f",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "biomass" / "ENSPRESO_BIOMASS.xlsx"


class EnspresoBiomassAvailability(EnspresoBiomass):
    """Dataset class for the ENSPRESO biomass potential data.

    This class inherits from EnspresoBiomass and
    provides methods to extract biomass availability"""

    name = "enspreso_biomass_availability"

    def __init__(self, source_path: Path | str | None):
        super().__init__(source_path=source_path)

    def _set_data(self) -> pd.DataFrame:
        return pd.read_excel(self.path, sheet_name="ENER - NUTS0 EnergyCom")

    # -------- methods ------------------------

    def get_availability_import(
        self, element: Carrier, biomass_types: list[str], scenario: str = "ENS_Med"
    ) -> Attribute:
        """
        Compute the import availability of a biomass carrier from ENSPRESO potentials.

        Filters the ENSPRESO NUTS0 energy-commodity potentials to the given
        scenario and energy-commodity codes, converts to GW, and derives the
        reference-year value per node plus its yearly variation relative to
        that reference year.

        :param element: The Carrier element for which to compute the import
        availability.
        :param biomass_types:
            List of biomass energy-commodity codes to filter the ENSPRESO data.
        :param scenario: The scenario for which to compute the import availability.

        Returns:
            Attribute: the element's `availability_import` attribute, updated
                with the computed data.
        """
        reference_year_values, yearly_variation = self._compute_availability_import(
            element=element, biomass_types=biomass_types, scenario=scenario
        )

        source = SourceInformation(
            description=(
                "Biomass import availability derived from ENSPRESO NUTS0 energy "
                f"commodity potentials {biomass_types}, scenario '{scenario}'. "
                "Values are converted from PJ/a to GW and interpolated to fill "
                "missing years; the yearly variation is expressed relative to "
                "the reference year."
            ),
            metadata=self.metadata,
        )
        return element.availability_import.set_data(
            source=source,
            df=reference_year_values,
            unit="GW",
            yearly_variations_df=yearly_variation,
        )

    def get_availability_import_scenario(
        self,
        element: Carrier,
        biomass_types: list[str],
        name: str,
        ens_scenario: str,
        suffix: str,
    ) -> Scenario:
        """
        Build a scenario variation of the import availability for a
        different ENSPRESO scenario, e.g. for a biomass sensitivity analysis.

        :param element: The Carrier element for which to compute the availability.
        :param biomass_types:
            List of biomass energy-commodity codes to filter the ENSPRESO data.
        :param name: The name of the scenario, e.g. 'biomass_low'.
        :param ens_scenario: The ENSPRESO scenario to read, e.g. 'ENS_Low'.
        :param suffix: Suffix of the generated files, e.g. 'low'.

        Returns:
            Scenario: Variation of `availability_import` for this ENSPRESO
                scenario.
        """
        reference_year_values, yearly_variation = self._compute_availability_import(
            element=element, biomass_types=biomass_types, scenario=ens_scenario
        )
        return Scenario(
            name,
            suffix=suffix,
            df=reference_year_values,
            yearly_variations_df=yearly_variation,
        )

    def _compute_availability_import(
        self, element: Carrier, biomass_types: list[str], scenario: str
    ) -> tuple[pd.Series, pd.DataFrame]:
        """
        Compute the reference-year import availability and its yearly
        variation from ENSPRESO potentials.

        :param element: The Carrier element for which to compute the availability.
        :param biomass_types:
            List of biomass energy-commodity codes to filter the ENSPRESO data.
        :param scenario: The ENSPRESO scenario to read, e.g. 'ENS_Med'.

        Returns:
            tuple: The reference-year import availability (GW) per node, and
                its yearly variation relative to that reference year.
        """
        potential = self._get_availability_import(
            biomass_types=biomass_types, scenario=scenario
        )
        potential = potential.groupby(["NUTS0", "Year"]).sum()["Value"].unstack()
        potential = (
            potential / Constants.GJ_PER_MWH * 1000 / Constants.HOURS_PER_YEAR
        )  # PJ/a -> GW
        potential = interpolate_missing_years(potential)

        nodes = pd.Index(element.model.config.system.set_nodes)
        common_nodes = nodes.intersection(potential.index)
        potential = potential.loc[common_nodes].sort_index()
        potential.index.name = "node"

        reference_year = element.settings.time.reference_year
        potential = potential.loc[:, reference_year:]
        yearly_variation = potential.div(potential[reference_year], axis=0)
        reference_year_values = potential[reference_year]
        reference_year_values.name = "availability_import"

        return reference_year_values, yearly_variation

    def get_availability_import_yearly(
        self, element: Carrier, biomass_types: list[str], scenario: str = "ENS_Med"
    ) -> Attribute:
        """
        Compute the yearly import availability of a biomass carrier from ENSPRESO
        potentials.

        Filters the ENSPRESO NUTS0 energy-commodity potentials to the given
        scenario and energy-commodity codes, converts to GWh

        :param element: The Carrier element for which to compute the import
        availability.
        :param biomass_types:
            List of biomass energy-commodity codes to filter the ENSPRESO data.
        :param scenario: The scenario for which to compute the import availability.

        Returns:
            Attribute: the element's `availability_import` attribute, updated
                with the computed data.
        """
        potential = self._get_availability_import(
            biomass_types=biomass_types, scenario=scenario
        )
        potential = potential.groupby(["NUTS0", "Year"]).sum()["Value"].unstack()
        potential = potential / Constants.GJ_PER_MWH * 1000  # PJ/a -> GWh
        potential = interpolate_missing_years(potential)

        nodes = pd.Index(element.model.config.system.set_nodes)
        common_nodes = nodes.intersection(potential.index)
        potential = potential.loc[common_nodes].sort_index()

        reference_year = element.settings.time.reference_year
        potential = potential.loc[:, reference_year:].T
        potential.index.name = "year"

        source = SourceInformation(
            description=(
                "Annual biomass import availability derived from ENSPRESO NUTS0 energy "
                f"commodity potentials {biomass_types}, scenario '{scenario}'. "
                "Values are converted from PJ/a to GWh and interpolated to fill "
                "missing years."
            ),
            metadata=self.metadata,
        )
        return element.availability_import_yearly.set_data(
            source=source,
            df=potential,
            unit="GWh",
        )

    def _get_availability_import(
        self, biomass_types: list[str], scenario: str = "ENS_Med"
    ) -> pd.DataFrame:
        """
        Compute the import availability of a biomass carrier from ENSPRESO potentials.

        Filters the ENSPRESO NUTS0 energy-commodity potentials to the given
        scenario and energy-commodity codes.

        :param biomass_types:
            List of biomass energy-commodity codes to filter the ENSPRESO data.
        :param scenario: The scenario for which to compute the import availability.

        Returns:
            potential: DataFrame with the availability of biomass per node and year.
        """
        potential = self.data[
            (self.data["Scenario"] == scenario)
            & (self.data["Energy Commodity"].isin(biomass_types))
        ]
        return potential


class EnspresoBiomassPrice(EnspresoBiomass):
    """Dataset class for the ENSPRESO biomass price data.

    This class inherits from EnspresoBiomass and
    provides methods to extract biomass price"""

    name = "enspreso_biomass_price"

    def __init__(self, source_path: Path | str | None):
        super().__init__(source_path=source_path)

    def _set_data(self) -> pd.DataFrame:
        return pd.read_excel(self.path, sheet_name="COST - NUTS0 EnergyCom")

    # -------- methods ------------------------

    def get_price_import(
        self,
        element: Carrier,
        biomass_types: list[str],
        scenario: str = "ENS_Med",
        regional_prices: bool = False,
    ) -> Attribute:
        """
        Compute the import price of a biomass carrier from ENSPRESO potentials.

        Filters the ENSPRESO NUTS0 energy-commodity prices to the given
        scenario and energy-commodity codes, converts from Euro/GJ to Euro/MWh,
        and derives the reference-year value per node plus its yearly variation
        relative to that reference year. When aggregating across multiple
        biomass types and/or regions, the average price is used, weighted by
        the availability of each biomass type in each region.

        :param element: The Carrier element for which to compute the import price.
        :param biomass_types: List of
            biomass energy-commodity codes to filter the ENSPRESO data.
        :param scenario: The scenario for which to compute the import price.
        :param regional_prices: Whether to use national prices. If False,
            the average price across all NUTS0 regions is used.

        Returns:
            Attribute: the element's `price_import` attribute, updated
                with the computed data.
        """
        table = self.data[
            (self.data["Scenario"] == scenario)
            & (self.data["Energy Commodity"].isin(biomass_types))
        ]
        table = table.set_index(["NUTS0", "Year", "Energy Commodity"])
        unit = table["Units"].unique()
        assert (
            len(unit) == 1
        ), f"Multiple units found in ENSPRESO biomass price data: {unit}"
        assert (
            unit[0] == "Euro2010/GJ"
        ), f"Unexpected unit in ENSPRESO biomass price data: {unit[0]}"
        data = table["NUTS0 Energy Commodity Cost "]

        nodes = pd.Index(element.model.config.system.set_nodes)
        common_nodes = nodes.intersection(data.index.get_level_values("NUTS0").unique())

        enspreso_availability = EnspresoBiomassAvailability(self.source_path)
        availability_table = enspreso_availability._get_availability_import(
            biomass_types=biomass_types, scenario=scenario
        )
        availability = availability_table.set_index(
            ["NUTS0", "Year", "Energy Commodity"]
        )["Value"]
        data = data.loc[common_nodes].sort_index()
        availability = availability.loc[common_nodes].sort_index()
        data_availability = data * availability

        price: pd.Series | pd.DataFrame
        if not regional_prices:
            price = (
                data_availability.groupby(["Year"]).sum()
                / availability.groupby(["Year"]).sum()
            )
        else:
            price = (
                data_availability.groupby(["NUTS0", "Year"]).sum()
                / availability.groupby(["NUTS0", "Year"]).sum()
            )
            price = price.unstack(level=0).T

        # Convert from 2010 Euro/GJ to Euro/MWh in the configured price year.
        price = price * Constants.GJ_PER_MWH
        inflation_rate = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=2010, target_year=element.settings.time.price_year
        )
        price = price * inflation_rate
        price = price.astype(float)

        price = interpolate_missing_years(price)

        reference_year = element.settings.time.reference_year

        df: pd.Series | None
        yearly_variation: pd.Series | pd.DataFrame
        if regional_prices:
            # national prices: one row per node, one column per year
            regional_price = cast(pd.DataFrame, price).loc[common_nodes].sort_index()
            regional_price.index.name = "node"
            regional_price = regional_price.loc[:, reference_year:]
            yearly_variation = regional_price.div(
                regional_price[reference_year], axis=0
            )
            df = regional_price[reference_year]
            df.name = "price_import"
            default_value = None
        else:
            # average price: one value per year
            average_price = cast(pd.Series, price).loc[reference_year:]
            default_value = cast(float, average_price[reference_year])
            yearly_variation = average_price.div(default_value)
            df = None
            yearly_variation.name = "price_import_yearly_variation"
            yearly_variation.index.name = "year"

        source = SourceInformation(
            description=(
                "Biomass import price derived from ENSPRESO NUTS0 energy "
                f"commodity prices {biomass_types}, scenario '{scenario}'. "
                "Values are converted from Euro/GJ to Euro/MWh and interpolated to "
                "fill missing years; the yearly variation is expressed relative to the "
                "reference year. If regional_prices is True, national prices are used; "
                "otherwise, the average price across all NUTS0 regions is used. The "
                "average price is weighted by the availability of each biomass type in "
                "each region."
            ),
            metadata=self.metadata,
        )

        return element.price_import.set_data(
            source=source,
            df=df,
            default_value=default_value,
            unit="Euro/MWh",
            yearly_variations_df=yearly_variation,
        )
