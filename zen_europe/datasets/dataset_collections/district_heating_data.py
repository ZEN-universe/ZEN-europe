from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


import pandas as pd
from zen_creator import Attribute, ConversionTechnology, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.dataset_collections.heat_demand import HeatDemand
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.datasets.datasets.technology.hre import HRE
from zen_europe.utils.utils import interpolate_missing_years


class DistrictHeatingData(DatasetCollection):
    """Extracting district heating cost data."""

    name = "district_heating_data"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "dea": DEA(self.source_path),
            "ecb": ECBInflation(self.source_path),
            "heat_demand": HeatDemand(self.settings, self.source_path),
            "eurostat": Eurostat(self.settings, self.source_path),
            "hre": HRE(self.source_path),
        }

    def get_capex_specific_conversion(self, element: ConversionTechnology) -> Attribute:
        """
        Get the district heating cost for the specified element.

        """
        heat_demand_dataset = cast(HeatDemand, self.data["heat_demand"])
        dea = cast(DEA, self.data["dea"])
        hd = heat_demand_dataset._calculate_demand(element)
        flh = (hd.sum() / hd.max()).median()  # GWh / GW
        rows = cast(
            pd.DataFrame,
            dea.get_dh_distribution_data().loc[("suburban", "capex", "ref"), :],
        )
        money_year_src = rows["money_year_src"].iloc[0]
        unit = rows["unit"].iloc[0]
        assert unit == "M€/km2", f"Unexpected unit for district heating cost: {unit}"
        cost = rows["value"]  # in M€/km2
        heat_density = 10  # GWh/(year*km2) - provided heat density for suburban areas
        capex_GWh = cost / heat_density  # in M€/(GWh / year)
        capex = capex_GWh * flh  # in M€/(GWh / year) -> M€ / GW -> € / kW
        ECB_dataset = cast(ECBInflation, self.data["ecb"])
        inflation = ECB_dataset.get_inflation_rate(
            base_year=int(money_year_src), target_year=self.settings.time.price_year
        )
        capex = capex * inflation
        capex = interpolate_missing_years(capex)
        capex = capex.loc[element.settings.time.years]
        capex.index.name = "year"
        capex.name = "capex_specific_conversion"

        source = SourceInformation(
            description=(
                "The specific capital expenditure (capex) for district heating grids "
                "is derived from the DEA dataset, which provides cost data for "
                "district heating infrastructure in Eur/m**2. The capex values are "
                "adjusted for inflation using the ECB Inflation dataset. The final "
                "capex values are expressed in Euro per kW, taking into account the "
                "average full load hours (flh) calculated from the heat demand data."
            ),
            metadata=self.metadata,
        )
        return element.capex_specific_conversion.set_data(
            source=source,
            df=capex,
            unit="Euro/kW",
        )

    def get_opex_specific_fixed(self, element: ConversionTechnology) -> Attribute:
        """
        Get the fixed operational expenditure (opex) for district heating grids.

        """
        dea = cast(DEA, self.data["dea"])
        rows = cast(
            pd.DataFrame,
            dea.get_dh_distribution_data().loc[("suburban", "fopex", "ref"), :],
        )
        money_year_src = rows["money_year_src"].iloc[0]
        unit = rows["unit"].iloc[0]
        assert unit == "€/MW/year", f"Unexpected unit for district heating cost: {unit}"
        cost = rows["value"]  # in €/MW/year
        cost = cost / 1000  # in €/kW/year
        cost = interpolate_missing_years(cost)
        cost = cost.loc[element.settings.time.years]
        ecb_dataset = cast(ECBInflation, self.data["ecb"])
        inflation = ecb_dataset.get_inflation_rate(
            base_year=int(money_year_src), target_year=self.settings.time.price_year
        )
        cost = cost * inflation
        source = SourceInformation(
            description=(
                "The fixed operational expenditure (opex) for district heating grids "
                "is obtained from the DEA dataset, which provides cost data for"
                " district heating infrastructure."
            ),
            metadata=self.metadata,
        )
        return element.opex_specific_fixed.set_data(
            source=source,
            df=cost,
            unit="Euro/kW",
        )

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """
        Get the variable operational expenditure (opex) for district heating grids.

        """
        dea = cast(DEA, self.data["dea"])
        rows = cast(
            pd.DataFrame,
            dea.get_dh_distribution_data().loc[("suburban", "vopex", "ref"), :],
        )
        money_year_src = rows["money_year_src"].iloc[0]
        unit = rows["unit"].iloc[0]
        assert unit == "€/MWh", f"Unexpected unit for district heating cost: {unit}"
        cost = rows["value"]  # in €/MWh
        cost = interpolate_missing_years(cost)
        cost = cost.loc[element.settings.time.years]
        ecb_dataset = cast(ECBInflation, self.data["ecb"])
        inflation = ecb_dataset.get_inflation_rate(
            base_year=int(money_year_src), target_year=self.settings.time.price_year
        )
        cost = cost * inflation
        default_value = cost.iloc[0]
        source = SourceInformation(
            description=(
                "The variable operational expenditure (opex) for district heating "
                "grids is obtained from the DEA dataset, which provides cost data for "
                "district heating infrastructure."
            ),
            metadata=self.metadata,
        )
        return element.opex_specific_variable.set_data(
            source=source,
            default_value=default_value,
            unit="Euro/MWh",
        )

    def get_capacity_limit(self, element: ConversionTechnology) -> Attribute:
        """
        Get the capacity limit for district heating grids.

        """
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        share_regions = eurostat_dataset.get_population_by_urbanization()
        share_regions = share_regions[eurostat_dataset.eurostat_year].unstack()
        hre = cast(HRE, self.data["hre"])
        potential = cast(pd.Series, hre.get_district_heating_potential().squeeze())
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            potential.index
        )
        common_nodes = (
            pd.Index(share_regions.columns)
            .intersection(potential.index)
            .intersection(element.model.config.system.set_nodes)
        )
        # imported here because sklearn is slow to import and this is the only
        # use of it
        from sklearn.linear_model import LinearRegression

        X = share_regions.loc[:, common_nodes].T
        y = potential.loc[common_nodes]
        reg = LinearRegression(fit_intercept=False).fit(X, y)
        predicted = reg.predict(share_regions.loc[:, missing_countries].T)
        predicted = pd.Series(predicted.squeeze(), index=missing_countries)
        potential_comb = pd.concat([potential, predicted])
        # multiply with peak demand
        heat_demand_dataset = cast(HeatDemand, self.data["heat_demand"])
        hd = heat_demand_dataset._calculate_demand(element)
        peak_demand = hd.max()
        capacity_limit = potential_comb * peak_demand
        capacity_limit.index.name = "node"
        capacity_limit.name = "capacity_limit"
        source = SourceInformation(
            description=(
                "The capacity limit for district heating grids is derived from the HRE "
                "dataset, which provides data on the potential for district heating in "
                "different regions. For countries with missing data, a linear "
                "regression model is used to predict the potential based on the share "
                "of the population in urban, suburban, and rural areas obtained from "
                "the Eurostat dataset. The final capacity limit is calculated by "
                "multiplying the district heating potential by the peak heat demand."
            ),
            metadata=self.metadata,
        )
        return element.capacity_limit.set_data(
            source=source,
            df=capacity_limit,
            unit="GW",
        )
