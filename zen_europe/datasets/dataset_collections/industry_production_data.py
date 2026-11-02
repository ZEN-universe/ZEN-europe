from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)

from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.carrier.faostat_food import FAOSTATFood
from zen_europe.datasets.datasets.carrier.jrc_bat_paper import JRCBATPaper
from zen_europe.datasets.datasets.carrier.jrc_idees import JRCIDEES
from zen_europe.datasets.datasets.carrier.rehfeldt2017 import Rehfeldt2017
from zen_europe.datasets.datasets.carrier.wolf2017 import Wolf2017
from zen_europe.datasets.datasets.energy_system.worldbank_population import (
    WorldBankPopulation,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.datasets.datasets.technology.cement_production_gardarsdottir import (
    CementProductionGardarsdottir,
)
from zen_europe.datasets.datasets.technology.industry_general_assumptions import (
    IndustryGeneralAssumptions,
)
from zen_europe.datasets.datasets.technology.industry_production_costs import (
    IndustryProductionCosts,
)
from zen_europe.datasets.datasets.technology.jrc_eu_times_industry import (
    BASE_YEAR,
    JRCEUTIMESIndustry,
)
from zen_europe.utils.constants import Constants
from zen_europe.utils.industry import (
    DATA_YEAR,
    HEAT_LEVELS,
    IDEES_EU,
    PROXY_NODES,
    SECTORS,
    kiln_fuel,
    model_nodes,
    spread_capacity_existing,
)
from zen_europe.utils.utils import instance_cache

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings

# a production series or frame, see `_to_t_per_hour`
ProductionT = TypeVar("ProductionT", pd.Series, pd.DataFrame)
# nodes scaled from their proxy node by population (World Bank)
POPULATION_SCALED = ("UK",)
# JRC-EU-TIMES processes of the glass routes and paper sub-processes
JRC_PROCESSES = {
    "glass": {
        "container": "IGHHOLLOW01",
        "flat": "IGFFLATGL01",
        "fibre": "IGFFLATGL01",
    },
    "paper": {
        "paper": "IPPHIGQUA01",
        "recovered_fibres": "IPPLOWQUA01",
        "chemical_pulp": "IPPPUPCHE01",
    },
}
# FAOSTAT item of each Rehfeldt (2017) food sub-process
FOOD_ITEMS = {
    "dairy": "Milk, Total",
    "meat_processing": "Meat, Total",
    "brewing": "Beer of barley, malted",
    "bread_bakery": "Wheat",
    "sugar": "Raw cane or beet sugar (centrifugal only)",
}


class IndustryProductionData(DatasetCollection):
    """Production technologies, product demand and fuel mix of the industry sectors."""

    name = "industry_production_data"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any]]:
        """Load all available data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "rehfeldt2017": Rehfeldt2017(self.source_path),
            "aidres": Aidres(self.source_path),
            "wolf2017": Wolf2017(self.source_path),
            "jrc_idees": JRCIDEES(self.source_path),
            "faostat_food": FAOSTATFood(self.source_path),
            "jrc_bat_paper": JRCBATPaper(self.source_path),
            "jrc_eu_times_industry": JRCEUTIMESIndustry(self.source_path),
            "cement_production_gardarsdottir": CementProductionGardarsdottir(
                self.source_path
            ),
            "dea": DEA(self.source_path),
            "ecb": ECBInflation(self.source_path),
            "worldbank_population": WorldBankPopulation(self.source_path),
            "industry_production_costs": IndustryProductionCosts(self.source_path),
            "industry_general_assumptions": IndustryGeneralAssumptions(
                self.source_path
            ),
        }

    # ---------- carriers ----------

    def get_demand(self, element: Element) -> Attribute:
        """
        Get the product demand of an industry sector.

        The demand equals today's physical production, flat over the year.
        """
        return element.demand.set_data(
            default_value=0.0,
            unit="tproduct/h",
            df=self.calculate_demand(element.sector, model_nodes(element)),
            source=SourceInformation(
                description=(
                    f"The {element.sector} demand equals today's physical production, "
                    "flat over the 8760 hours of the year. The production is taken "
                    "from the JRC-IDEES physical output (glass, paper), derived from "
                    "the JRC-IDEES thermal energy consumption and the Rehfeldt et al. "
                    "(2017) fuel intensity (ceramic), or from the Rehfeldt et al. "
                    "(2017) activity split by the FAOSTAT production (food). Nodes "
                    "without JRC-IDEES data use a proxy node (CH as AT, NO as FI, UK "
                    "as DE scaled by the World Bank population); for paper, their "
                    "consumption from the JRC BAT reference document is used."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- production technologies ----------

    def get_input_carrier(self, element: Element) -> Attribute:
        """Get the input carriers of a production technology: fuels, heat bands and
        electricity."""
        carriers = [
            *self._calculate_fuel_inputs(element.sector).index,
            *[
                element.heat_carrier(level)
                for level in self._active_heat_levels(element)
            ],
            "electricity",
        ]
        return element.input_carrier.set_data(
            default_value=carriers,
            source=SourceInformation(
                description=(
                    "The fuels are the JRC-IDEES thermal energy carriers of the "
                    f"sector with a share of at least "
                    f"{self._assumptions.get_value('fuel_share_cutoff'):.0%} "
                    "(general industry assumptions)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_conversion_factor(self, element: Element) -> Attribute:
        """
        Get the conversion factor of a production technology.

        The fuel (above 200 °C), heat (per temperature band) and electricity demand
        per tonne of product.
        """
        sector = element.sector
        energy = self.calculate_energy_intensity(sector)
        heat = self.calculate_heat_conversion_factors(sector)
        efficiency = self._assumptions.get_value("reference_boiler_efficiency")
        switchable = self._assumptions.get_value("kiln_switchable_share", "ceramic")
        unit = "GW/(tproduct/h)"
        cf = [
            {carrier: {"default_value": value, "unit": unit}}
            for carrier, value in self.calculate_fuel_intensity(sector).items()
        ]
        cf.append(
            {
                "electricity": {
                    "default_value": round(energy["electricity"], 12),
                    "unit": unit,
                }
            }
        )
        cf += [
            {
                element.heat_carrier(level): {
                    "default_value": round(heat[level], 12),
                    "unit": unit,
                }
            }
            for level in self._active_heat_levels(element)
        ]
        return element.conversion_factor.set_data(
            default_value=cf,
            source=SourceInformation(
                description=(
                    "The energy intensity is the activity-weighted energy intensity of "
                    "the sector's sub-processes from Rehfeldt et al. (2017) (glass: "
                    "AIDRES (2023) routes, weighted by EU production share). Heat "
                    "below 200 °C is split into temperature bands with the Rehfeldt "
                    "temperature distribution and, for 100-200 °C, with Wolf (2017), "
                    "and converted from final energy to useful heat with a reference "
                    f"boiler efficiency of {efficiency:.0%}; the rest is fuel, split "
                    "by the JRC-IDEES fuel mix. The natural gas of glass and ceramic "
                    "is supplied as kiln fuel; for ceramic, an assumed "
                    f"{switchable:.1%} of it can switch fuel, since the ceramic BREF "
                    "(JRC, Final Draft, April 2026, Sections 4.2.1-4.2.3) limits "
                    "electrified kilns to below 1600 °C and the > 1000 °C share of "
                    "technical ceramics in Rehfeldt et al. (2017) is treated as not "
                    "switchable."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing(self, element: Element) -> Attribute:
        """Get the existing production capacity, built evenly over the lifetime."""
        capacity = self._calculate_capacity(model_nodes(element))[element.sector]
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="tproduct/h",
            df=spread_capacity_existing(capacity, element),
            source=SourceInformation(
                description=(
                    "The existing production capacity is the JRC-IDEES installed "
                    "capacity (glass, paper) at 8760 hours per year; for ceramic, "
                    "food and the paper nodes without JRC-IDEES data it is the "
                    "product demand (see demand) divided by an assumed capacity "
                    "utilisation of "
                    f"{self._assumptions.get_value('capacity_utilisation')} "
                    "(general industry assumptions). It is assumed to be built "
                    "evenly over the lifetime of the technology."
                ),
                metadata=self.metadata,
            ),
        )

    def get_lifetime(self, element: Element) -> Attribute:
        """Get the lifetime from JRC-EU-TIMES or the sector's cost proxy."""
        if element.sector == "ceramic":
            return self._get_ceramic_cost(element, "get_lifetime")
        return element.lifetime.set_data(
            default_value=float(self._costs.at[element.sector, "lifetime"]),
            source=self._cost_source(element.sector, "lifetime"),
        )

    def get_capex_specific_conversion(self, element: Element) -> Attribute:
        """Get the investment cost, see docs, "Production technologies"."""
        if element.sector == "ceramic":
            return self._get_ceramic_cost(element, "get_capex_specific")
        return element.capex_specific_conversion.set_data(
            default_value=float(self._costs.at[element.sector, "capex"]),
            unit="Euro/(tproduct/h)",
            source=self._cost_source(element.sector, "capex"),
        )

    def get_opex_specific_fixed(self, element: Element) -> Attribute:
        """Get the fixed O&M cost."""
        if element.sector == "ceramic":
            return self._get_ceramic_cost(element, "get_opex_specific_fixed")
        return element.opex_specific_fixed.set_data(
            default_value=float(self._costs.at[element.sector, "opex_fixed"]),
            unit="Euro/(tproduct/h)",
            source=self._cost_source(element.sector, "opex_fixed"),
        )

    def get_opex_specific_variable(self, element: Element) -> Attribute:
        """Get the variable O&M cost, without energy."""
        if element.sector == "ceramic":
            return self._get_ceramic_cost(element, "get_opex_specific_variable")
        return element.opex_specific_variable.set_data(
            default_value=float(self._costs.at[element.sector, "opex_variable"]),
            unit="Euro/tproduct",
            source=self._cost_source(element.sector, "opex_variable"),
        )

    def get_carbon_intensity_technology(self, element: Element) -> Attribute:
        """Get the process CO2 emissions."""
        assumptions = self._assumptions
        intensity = assumptions.get_value("carbon_intensity", element.sector)
        return element.carbon_intensity_technology.set_data(
            default_value=intensity,
            unit=assumptions.get_unit("carbon_intensity", element.sector),
            source=AssumptionInformation(
                description=(
                    f"The process CO2 emissions of {element.sector} production are "
                    f"{intensity} t per t of product. "
                    + assumptions.get_description("carbon_intensity", element.sector)
                    + " See docs, 'Production technologies'."
                ),
            ),
        )

    # ---------- post-combustion capture ----------

    def get_conversion_factor_post_comb(self, element: Element) -> Attribute:
        """
        Get the conversion factor of the post-combustion capture of a sector.

        The capture unit is the one of cement_post_comb; its heat is supplied by the
        sector's natural gas and coal, split by the sector's fuel mix.
        """
        dea = cast(DEA, self.data["dea"])
        cement = {
            carrier: values["default_value"]
            for entry in dea.get_conversion_factor_cement_post_comb()
            for carrier, values in entry.items()
        }
        shares = self.calculate_fuel_shares(element.sector)
        heat_fuels = shares[shares.index.isin(["natural_gas", "hard_coal"])]
        heat_fuels = heat_fuels / heat_fuels.sum()
        # unit of the DEA capture unit, converted by ZEN-creator as for cement
        unit = "GWh/kilotCO2"
        cf = [
            {
                carrier: {
                    "default_value": round(cement["fuel_for_cement"] * share, 12),
                    "unit": unit,
                }
            }
            for carrier, share in heat_fuels.items()
        ]
        cf += [
            {carrier: {"default_value": cement[carrier], "unit": unit}}
            for carrier in ("electricity", "district_heat")
        ]
        return element.conversion_factor.set_data(
            default_value=cf,
            source=SourceInformation(
                description=(
                    "The capture unit is the DEA post-combustion capture unit of "
                    "cement_post_comb. Its heat demand is supplied by the sector's "
                    "natural gas and coal, split by the sector's JRC-IDEES fuel mix."
                ),
                metadata=self.metadata,
            ),
        )

    def get_retrofit_flow_coupling_factor(self, element: Element) -> Attribute:
        """Get the captured process CO2 per tonne of product."""
        dea = cast(DEA, self.data["dea"])
        capture_rate = dea.get_capture_rate_CCS()
        intensity = self._assumptions.get_value("carbon_intensity", element.sector)
        return element.retrofit_flow_coupling_factor.set_data(
            default_value=round(intensity * capture_rate, 12),
            unit="tCO2/tproduct",
            base_technology=element.base_technology_name,
            source=SourceInformation(
                description=(
                    f"The process emissions of {intensity} t CO2 per t of product "
                    f"times the DEA capture rate of {capture_rate:.0%}."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- data used by other collections ----------

    def calculate_demand(self, sector: str, nodes: tuple[str, ...]) -> pd.Series:
        """Product demand (t/h): the physical production, named as the demand."""
        return (
            self.calculate_production(sector, nodes)
            .rename("demand")
            .rename_axis("node")
        )

    def calculate_production(self, sector: str, nodes: tuple[str, ...]) -> pd.Series:
        """Physical production (t/h), averaged over the year."""
        return self._calculate_production(nodes)[sector]

    def calculate_energy_intensity(self, sector: str) -> pd.Series:
        """Fuel (above 200 °C), heat and electricity demand (GW per t/h)."""
        parameters = self._sector_parameters.loc[sector]
        energy = pd.Series(
            {
                "fuel": parameters["fuel"],
                "heat_0_100": parameters["heat_0_100"],
                "heat_100_200": parameters["heat_100_200"],
                "heat": parameters["heat_0_100"] + parameters["heat_100_200"],
                "electricity": parameters["electricity"],
            }
        )
        return energy / Constants.SECONDS_PER_HOUR  # GJ/t -> GW/(t/h)

    def calculate_fuel_intensity(self, sector: str) -> pd.Series:
        """Fuel demand (GW per t/h) per fuel carrier, incl. the kiln fuel."""
        fuel = self.calculate_energy_intensity(sector)["fuel"]
        return (fuel * self._calculate_fuel_inputs(sector)).round(12)

    def calculate_heat_conversion_factors(self, sector: str) -> pd.Series:
        """Heat demand per band (GW per t/h), 100-200 °C split by Wolf (2017)."""
        energy = self.calculate_energy_intensity(sector)
        wolf = cast(Wolf2017, self.data["wolf2017"])
        split = wolf.get_temperature_split().loc[sector]
        return pd.Series(
            {
                "0_100": energy["heat_0_100"],
                "100_150": energy["heat_100_200"] * split["100_150"],
                "150_200": energy["heat_100_200"] * split["150_200"],
            }
        )

    def calculate_fuel_shares(self, sector: str) -> pd.Series:
        """Fuel mix of the sector's thermal energy (EU27), small fuels dropped."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        thermal = idees.get_industry_thermal_final_energy_by_fuel(
            sector, DATA_YEAR, "production"
        ).loc[IDEES_EU]
        shares = (thermal / thermal.sum()).drop("other", errors="ignore")
        shares = shares[shares >= self._assumptions.get_value("fuel_share_cutoff")]
        return shares / shares.sum()

    # ---------- helpers ----------

    @property
    def _assumptions(self) -> IndustryGeneralAssumptions:
        return cast(
            IndustryGeneralAssumptions, self.data["industry_general_assumptions"]
        )

    def _calculate_fuel_inputs(self, sector: str) -> pd.Series:
        """Fuel shares, with the switchable kiln natural gas as kiln fuel."""
        shares = self.calculate_fuel_shares(sector)
        assumptions = self._assumptions
        if (
            not assumptions.has_value("kiln_switchable_share", sector)
            or "natural_gas" not in shares
        ):
            return shares
        switchable = assumptions.get_value("kiln_switchable_share", sector)
        natural_gas = shares.pop("natural_gas")
        shares[kiln_fuel(sector)] = natural_gas * switchable
        if natural_gas * (1 - switchable) > 1e-12:
            shares["natural_gas"] = natural_gas * (1 - switchable)
        return shares

    def _active_heat_levels(self, element: Element) -> list[str]:
        heat = self.calculate_heat_conversion_factors(element.sector)
        return [level for level in HEAT_LEVELS if heat[level] > 0]

    @instance_cache
    def _calculate_capacity(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Installed production capacity (t/h) per node and sector; the production
        divided by the capacity utilisation where no capacity data exist."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        production = self._calculate_production(nodes)
        utilisation = self._assumptions.get_value("capacity_utilisation")
        capacity = production / utilisation
        capacity["glass"] = self._to_t_per_hour(
            self._fill_proxy_nodes(
                self._reindex_nodes(
                    idees.get_industry_installed_capacity("glass", DATA_YEAR), nodes
                )
            )
        )
        capacity["paper"] = self._to_t_per_hour(
            self._reindex_nodes(
                idees.get_industry_installed_capacity("paper", DATA_YEAR), nodes
            )
        )
        # paper: the nodes without JRC-IDEES (JRC BAT consumption)
        jrc_bat = cast(JRCBATPaper, self.data["jrc_bat_paper"])
        bat_nodes = jrc_bat.get_consumption().index
        capacity.loc[bat_nodes, "paper"] = (
            production.loc[bat_nodes, "paper"] / utilisation
        )
        return capacity

    @instance_cache
    def _calculate_production(self, nodes: tuple[str, ...]) -> pd.DataFrame:
        """Physical production (t/h) averaged over the year, per node and sector."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        production = self._to_t_per_hour(
            pd.DataFrame(
                {
                    "glass": self._fill_proxy_nodes(
                        self._reindex_nodes(
                            idees.get_industry_physical_output("glass", DATA_YEAR),
                            nodes,
                        )
                    ),
                    "ceramic": self._calculate_ceramic_output(nodes),
                    "paper": self._reindex_nodes(
                        idees.get_industry_physical_output("paper", DATA_YEAR), nodes
                    ),
                }
            )
        )
        production["food"] = self._calculate_food_production(nodes)
        # paper: the consumption of the nodes without JRC-IDEES (JRC BAT)
        jrc_bat = cast(JRCBATPaper, self.data["jrc_bat_paper"])
        consumption = jrc_bat.get_consumption()
        production.loc[consumption.index, "paper"] = self._to_t_per_hour(consumption)
        return production

    @instance_cache
    def _calculate_ceramic_output(self, nodes: tuple[str, ...]) -> pd.Series:
        """Ceramic output (kt/a): JRC-IDEES thermal energy / Rehfeldt fuel intensity."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        thermal = idees.get_industry_thermal_final_energy("ceramic", DATA_YEAR).sum(
            axis=1
        )  # ktoe
        intensity = self._sector_parameters.at["ceramic", "fuel_total"]  # GJ/t
        output = thermal * Constants.GJ_PER_KTOE / (intensity * 1000)
        return self._fill_proxy_nodes(self._reindex_nodes(output, nodes))

    @instance_cache
    def _calculate_food_production(self, nodes: tuple[str, ...]) -> pd.Series:
        """Food production (t/h): Rehfeldt (2017) activity split by FAOSTAT
        production."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        faostat = cast(FAOSTATFood, self.data["faostat_food"])
        activity = rehfeldt.get_sub_processes("food").loc[
            list(FOOD_ITEMS), "activity_Mt"
        ]
        production = faostat.get_production(DATA_YEAR)
        production = production.reindex(
            index=list(FOOD_ITEMS.values()),
            columns=list(nodes),
            fill_value=0.0,
        )
        production.index = list(FOOD_ITEMS)
        shares = production.div(production.sum(axis=1), axis=0).fillna(0.0)
        activity = shares.mul(activity, axis=0).sum()  # Mt/a
        return activity * 1e6 / Constants.HOURS_PER_YEAR  # Mt/a -> t/h

    @staticmethod
    def _to_t_per_hour(data: ProductionT) -> ProductionT:
        """Convert a production from kt/a to t/h."""
        return data * 1000.0 / Constants.HOURS_PER_YEAR

    @staticmethod
    def _reindex_nodes(data: pd.Series, nodes: tuple[str, ...]) -> pd.Series:
        """Select the model nodes; nodes without data are 0."""
        return data.reindex(list(nodes), fill_value=0.0)

    def _fill_proxy_nodes(self, data: pd.Series) -> pd.Series:
        """Fill the nodes without JRC-IDEES data from their proxy node, scaled by
        the population ratio for the nodes in POPULATION_SCALED."""
        data = data.copy()
        for node, proxy in PROXY_NODES.items():
            data[node] = data[proxy] * self._proxy_factor(node, proxy)
        return data

    def _proxy_factor(self, node: str, proxy: str) -> float:
        """Population of `node` per population of `proxy` (World Bank)."""
        if node not in POPULATION_SCALED:
            return 1.0
        worldbank = cast(WorldBankPopulation, self.data["worldbank_population"])
        population = worldbank.get_population([node, proxy], [DATA_YEAR])[DATA_YEAR]
        return float(population[node] / population[proxy])

    @cached_property
    def _sector_parameters(self) -> pd.DataFrame:
        """Energy intensity (GJ/t) per sector, heat split by temperature. The heat
        is useful heat: the final energy below 200 °C times the reference boiler
        efficiency."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        aidres = cast(Aidres, self.data["aidres"])
        efficiency = self._assumptions.get_value("reference_boiler_efficiency")
        parameters = {}
        for sector in SECTORS:
            if sector == "glass":
                energy = aidres.get_sub_processes_glass().rename(
                    columns={"ng_GJ_t": "fuel"}
                )
                weights = aidres.get_production_shares_glass()
            else:
                energy = rehfeldt.get_sub_processes(sector).rename(
                    columns={"fuels_GJ_t": "fuel"}
                )
                weights = rehfeldt.get_activity_weights(sector)
            temperatures = rehfeldt.get_sub_processes(sector)
            fuel = weights.dot(energy.loc[weights.index, "fuel"])
            share_0_100 = weights.dot(temperatures.loc[weights.index, "temp_lt100"])
            share_100_200 = weights.dot(temperatures.loc[weights.index, "temp_100_200"])
            parameters[sector] = {
                "fuel_total": fuel,
                "fuel": fuel * (1.0 - share_0_100 - share_100_200),
                "heat_0_100": fuel * share_0_100 * efficiency,
                "heat_100_200": fuel * share_100_200 * efficiency,
                "electricity": weights.dot(energy.loc[weights.index, "elec_GJ_t"]),
            }
        return pd.DataFrame.from_dict(parameters, orient="index")

    @cached_property
    def _costs(self) -> pd.DataFrame:
        """Lifetime and costs of glass, paper and food, see docs, "Production
        technologies"."""
        aidres = cast(Aidres, self.data["aidres"])
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        hours = Constants.HOURS_PER_YEAR
        costs = {
            "glass": self._calculate_jrc_costs(
                "glass", aidres.get_production_shares_glass()
            ),
            "paper": self._calculate_jrc_costs(
                "paper", rehfeldt.get_activity_weights("paper")
            ),
        }
        # only the paper capex is taken from the literature; the O&M costs and the
        # lifetime stay those of the JRC-EU-TIMES integrated mill. Paper has no
        # competing production route, so this only offsets the costs linearly.
        # Euro/(t/a) -> Euro/(t/h)
        costs["paper"]["capex"] = round(
            self._literature_cost("paper", "capex") * hours, 2
        )
        costs["food"] = {
            "capex": round(self._literature_cost("food", "capex") * hours, 2),
            "opex_fixed": round(self._literature_cost("food", "opex_fixed") * hours, 2),
            "opex_variable": self._literature_cost("food", "opex_variable"),
            "lifetime": self._literature_cost("food", "lifetime"),
        }
        return pd.DataFrame.from_dict(costs, orient="index")

    def _literature_cost(self, sector: str, parameter: str) -> float:
        """Literature cost, inflated from its price year if it has one."""
        literature = cast(
            IndustryProductionCosts, self.data["industry_production_costs"]
        )
        value = literature.get_value(sector, parameter)
        price_year = literature.get_price_year(sector, parameter)
        if price_year is None:
            return value
        ecb = cast(ECBInflation, self.data["ecb"])
        return value * ecb.get_inflation_rate(price_year, self.settings.cost.price_year)

    def _calculate_jrc_costs(self, sector: str, weights: pd.Series) -> dict[str, float]:
        """Weighted JRC-EU-TIMES costs of the sector's processes."""
        times = cast(JRCEUTIMESIndustry, self.data["jrc_eu_times_industry"])
        ecb = cast(ECBInflation, self.data["ecb"])
        inflation = ecb.get_inflation_rate(BASE_YEAR, self.settings.cost.price_year)
        parameters = pd.DataFrame(
            {
                sub_process: times.get_process_parameters(process)
                for sub_process, process in JRC_PROCESSES[sector].items()
            }
        )
        weighted = parameters.dot(weights[parameters.columns])
        hours = Constants.HOURS_PER_YEAR
        return {
            # Euro/(t/a) -> Euro/(t/h)
            "capex": weighted["INVCOST"] * inflation * hours,
            "opex_fixed": weighted["FIXOM"] * inflation * hours,
            "opex_variable": weighted["VAROM"] * inflation,
            "lifetime": round(weighted["LIFE"]),
        }

    def _get_ceramic_cost(self, element: Element, method: str) -> Attribute:
        """Cost or lifetime of the Gardarsdottir et al. (2019) cement plant."""
        gardarsdottir = cast(
            CementProductionGardarsdottir, self.data["cement_production_gardarsdottir"]
        )
        return getattr(gardarsdottir, method)(element).set_data(
            source=AssumptionInformation(
                description=(
                    "No cost data for ceramic production exist; the cement clinker "
                    "plant of Gardarsdottir et al. (2019), Comparison of Technologies "
                    "for CO2 Capture from Cement Production - Part 2: Cost Analysis, "
                    "Energies 12, 542, doi:10.3390/en12030542, is used as a proxy for "
                    "a kiln-fired mineral product."
                )
            ),
        )

    def _cost_source(
        self, sector: str, attribute: str
    ) -> SourceInformation | AssumptionInformation:
        """Source of a cost or the lifetime of a production technology."""
        inflation = (
            f"Costs in {self.settings.cost.price_year} Euro using ECB HICP "
            "inflation, see docs, 'Production technologies'."
        )
        literature = cast(
            IndustryProductionCosts, self.data["industry_production_costs"]
        )
        if sector == "food":
            description = literature.get_description(sector, attribute)
            return AssumptionInformation(description=f"{description} {inflation}")
        if sector == "paper" and attribute == "capex":
            return AssumptionInformation(
                description=literature.get_description(sector, attribute),
            )
        descriptions = {
            "glass": (
                "JRC-EU-TIMES costs and lifetime of the glass processes, weighted by "
                "the AIDRES (2023) EU production shares of the glass routes."
            ),
            "paper": (
                "JRC-EU-TIMES costs and lifetime of the paper processes, weighted by "
                "the Rehfeldt et al. (2017) activity."
            ),
        }
        return SourceInformation(
            description=f"{descriptions[sector]} {inflation}",
            metadata=self.metadata,
        )
