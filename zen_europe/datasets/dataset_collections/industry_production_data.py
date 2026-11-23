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

from zen_europe.datasets.datasets.carrier.jrc_idees import IDEES_EU, JRCIDEES
from zen_europe.datasets.datasets.carrier.rehfeldt2017 import Rehfeldt2017
from zen_europe.datasets.datasets.carrier.wolf2017 import Wolf2017
from zen_europe.datasets.datasets.energy_system.worldbank_population import (
    WorldBankPopulation,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.jrc_eu_times_industry import (
    JRCEUTIMESIndustry,
)
from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
)

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings

# year of the production, energy and heat statistics of the industry heat sectors
DATA_YEAR = 2023
# proxy node of the nodes without JRC-IDEES data: CH as AT, NO as FI, UK as DE
PROXY_NODES = {"CH": "AT", "NO": "FI", "UK": "DE"}
# a production series or frame, see `to_t_per_hour`
ProductionT = TypeVar("ProductionT", pd.Series, pd.DataFrame)
# fuels below this share of a sector's JRC-IDEES thermal fuel mix (> 200 °C) are
# dropped, so the production technologies only take the main fuels
FUEL_SHARE_CUTOFF = 0.1
# sectors whose JRC-IDEES capacity utilisation sets the existing production capacity
# where no capacity data exist (ceramic, food, paper at CH, NO and UK)
CAPACITY_DATA_SECTORS = ("glass", "paper")


class IndustryProductionData(DatasetCollection):
    """Data shared by the production data of the industry sectors (glass, ceramic,
    paper, food): energy intensity and heat bands, fuel mix, capacity utilisation,
    proxy nodes, lifetime and the attributes of the production technologies."""

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
            "wolf2017": Wolf2017(self.source_path),
            "jrc_idees": JRCIDEES(self.source_path),
            "dea": DEA(self.source_path),
            "worldbank_population": WorldBankPopulation(self.source_path),
            "jrc_eu_times_industry": JRCEUTIMESIndustry(self.source_path),
        }

    # ---------- attributes of the products and production technologies ----------

    def get_demand(
        self, element: Element, production: pd.Series, description: str
    ) -> Attribute:
        """Get the product demand: today's physical production `production` (t/h),
        flat over the year."""
        return element.demand.set_data(
            default_value=0.0,
            unit="tproduct/h",
            df=production.rename("demand").rename_axis("node"),
            source=SourceInformation(
                description=(
                    "The demand equals today's physical production, flat over the "
                    f"8760 hours of the year. {description}"
                ),
                metadata=self.metadata,
            ),
        )

    def get_input_carrier(
        self, element: Element, conversion_factors: pd.Series, description: str
    ) -> Attribute:
        """Get the input carriers of a production technology: the carriers of its
        `conversion_factors`."""
        return element.input_carrier.set_data(
            default_value=list(conversion_factors.index),
            source=SourceInformation(description=description, metadata=self.metadata),
        )

    def get_conversion_factor(
        self, element: Element, conversion_factors: pd.Series, description: str
    ) -> Attribute:
        """Get the conversion factor of a production technology: the energy demand
        `conversion_factors` (GW per t/h) per input carrier."""
        unit = "GW/(tproduct/h)"
        return element.conversion_factor.set_data(
            default_value=[
                {carrier: {"default_value": float(value), "unit": unit}}
                for carrier, value in conversion_factors.items()
            ],
            source=SourceInformation(
                description=(
                    f"{description} heat below 200 °C is split into temperature bands "
                    "with the Rehfeldt et al. (2017) temperature distribution and, for "
                    "100-200 °C, with Wolf (2017), and converted from final energy to "
                    "useful heat with a reference boiler efficiency of "
                    f"{self.reference_boiler_efficiency:.1%}, the mean efficiency of "
                    "the DEA industrial boilers."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_existing(
        self, element: Element, capacity: pd.Series, description: str
    ) -> Attribute:
        """Get the existing production capacity `capacity` (t/h), built evenly over
        the lifetime."""
        data = capacity.to_frame(element.settings.time.reference_year - 1)
        capacity_addition = calculate_capacity_addition_from_cumulative(data, element)
        return element.capacity_existing.set_data(
            default_value=0.0,
            unit="tproduct/h",
            df=format_capacity_existing(capacity_addition),
            source=SourceInformation(
                description=(
                    f"{description} It is assumed to be built evenly over the "
                    "lifetime of the technology."
                ),
                metadata=self.metadata,
            ),
        )

    def describe_capacity_utilisation(self) -> str:
        """Description of the capacity utilisation."""
        return (
            f"a capacity utilisation of {self.capacity_utilisation:.3f}, the mean "
            "ratio of EU27 physical output and installed capacity of glass and paper "
            f"in JRC-IDEES-{DATA_YEAR}"
        )

    # ---------- post-combustion capture ----------

    def get_conversion_factor_post_comb(
        self, element: Element, fuel_shares: pd.Series
    ) -> Attribute:
        """
        Get the conversion factor of the post-combustion capture of a sector.

        The capture unit is the one of cement_post_comb; its heat is supplied by the
        sector's natural gas and coal, split by the sector's fuel mix `fuel_shares`.
        """
        dea = cast(DEA, self.data["dea"])
        cement = {
            carrier: values["default_value"]
            for entry in dea.get_conversion_factor_cement_post_comb()
            for carrier, values in entry.items()
        }
        heat_fuels = fuel_shares[fuel_shares.index.isin(["natural_gas", "hard_coal"])]
        heat_fuels = heat_fuels / heat_fuels.sum()
        # unit of the DEA capture unit, converted by ZEN-creator as for cement
        unit = "GWh/kilotCO2"
        cf = [
            {
                carrier: {
                    "default_value": round(cement["cement_fuel"] * share, 12),
                    "unit": unit,
                }
            }
            for carrier, share in heat_fuels.items()
        ]
        cf += [
            {carrier: {"default_value": cement[carrier], "unit": unit}}
            for carrier in ("electricity", "recoverable_waste_heat")
        ]
        return element.conversion_factor.set_data(
            default_value=cf,
            source=SourceInformation(
                description=(
                    "The capture unit is the DEA post-combustion capture unit of "
                    "cement_post_comb. Its heat demand is supplied by the sector's "
                    "natural gas and coal, split by the sector's fuel mix."
                ),
                metadata=self.metadata,
            ),
        )

    def get_retrofit_flow_coupling_factor_post_comb(
        self, element: Element, intensity: float
    ) -> Attribute:
        """Get the captured process CO2 per tonne of product, for process emissions
        of `intensity` t per t of product."""
        dea = cast(DEA, self.data["dea"])
        capture_rate = dea.get_capture_rate_CCS()
        return element.retrofit_flow_coupling_factor.set_data(
            default_value=round(intensity * capture_rate, 12),
            unit="tCO2/tproduct",
            base_technology=element.base_technology_name,
            source=SourceInformation(
                description=(
                    f"The process emissions of {intensity:.4f} t CO2 per t of product "
                    f"times the DEA capture rate of {capture_rate:.0%}."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- fuel retrofits ----------

    def get_lifetime_fuel_retrofit(self, element: Element) -> Attribute:
        """Get the lifetime of a fuel retrofit: that of its base technology, since the
        fuel supply is tied to the operation of the kiln or furnace."""
        base = element.model.conversion_technologies[element.base_technology_name]
        return element.lifetime.set_data(
            default_value=base.lifetime.default_value,
            unit=base.lifetime.unit,
            source=SourceInformation(
                description=(
                    f"As {element.base_technology_name}, since the fuel supply is "
                    "tied to the operation of the kiln or furnace."
                ),
                metadata=self.metadata,
            ),
        )

    def get_retrofit_flow_coupling_factor_fuel(
        self, element: Element, max_share: float, fuel_intensity: float, reason: str
    ) -> Attribute:
        """Get the sector fuel a fuel retrofit supplies at most per tonne of product:
        the fuel's maximum share `max_share` times the sector fuel demand
        `fuel_intensity` (GWh per t of product)."""
        sector = element.retrofit_reference_carrier.default_value[0]
        return element.retrofit_flow_coupling_factor.set_data(
            default_value=round(max_share * fuel_intensity, 12),
            unit="GWh/tproduct",
            base_technology=element.base_technology_name,
            source=SourceInformation(
                description=(
                    f"The maximum share of {max_share:.2%} of the {sector} demand "
                    f"({reason}) times the {sector} demand per tonne of product, see "
                    f"conversion_factor of {element.base_technology_name}."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- energy intensity ----------

    def calculate_energy_intensity(
        self, sector: str, fuel_total: float, electricity: float, weights: pd.Series
    ) -> pd.Series:
        """
        Fuel (above 200 °C), heat and electricity demand (GW per t/h) of a sector.

        `fuel_total` and `electricity` are the sector's final energy (GJ/t); the
        final energy below 200 °C follows the Rehfeldt et al. (2017) temperature
        distribution of the sector's sub-processes, weighted by `weights`, and is
        converted to useful heat with the reference boiler efficiency.
        """
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        temperatures = rehfeldt.get_sub_processes(sector).loc[weights.index]
        share_0_100 = weights.dot(temperatures["temp_lt100"])
        share_100_200 = weights.dot(temperatures["temp_100_200"])
        efficiency = self.reference_boiler_efficiency
        heat_0_100 = fuel_total * share_0_100 * efficiency
        heat_100_200 = fuel_total * share_100_200 * efficiency
        energy = pd.Series(
            {
                "fuel": fuel_total * (1.0 - share_0_100 - share_100_200),
                "heat_0_100": heat_0_100,
                "heat_100_200": heat_100_200,
                "heat": heat_0_100 + heat_100_200,
                "electricity": electricity,
            }
        )
        return energy / Constants.SECONDS_PER_HOUR  # GJ/t -> GW/(t/h)

    def calculate_energy_intensity_rehfeldt(self, sector: str) -> pd.Series:
        """Energy intensity (GW per t/h) of a sector from its Rehfeldt et al. (2017)
        sub-processes, weighted by activity."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        weights = rehfeldt.get_activity_weights(sector)
        electricity = weights.dot(rehfeldt.get_sub_processes(sector)["elec_GJ_t"])
        return self.calculate_energy_intensity(
            sector, self.calculate_fuel_total_rehfeldt(sector), electricity, weights
        )

    def calculate_fuel_total_rehfeldt(self, sector: str) -> float:
        """Total fuel (GJ/t) of a sector from its Rehfeldt et al. (2017)
        sub-processes, weighted by activity."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        weights = rehfeldt.get_activity_weights(sector)
        return float(weights.dot(rehfeldt.get_sub_processes(sector)["fuels_GJ_t"]))

    def calculate_heat_conversion_factors(
        self, sector: str, energy: pd.Series
    ) -> pd.Series:
        """Heat demand per band (GW per t/h) of the energy intensity `energy`;
        100-200 °C split by Wolf (2017)."""
        wolf = cast(Wolf2017, self.data["wolf2017"])
        split = wolf.get_temperature_split().loc[sector]
        return pd.Series(
            {
                "0_100": energy["heat_0_100"],
                "100_150": energy["heat_100_200"] * split["100_150"],
                "150_200": energy["heat_100_200"] * split["150_200"],
            }
        )

    def calculate_conversion_factors(
        self, sector: str, energy: pd.Series, fuel_inputs: pd.Series
    ) -> pd.Series:
        """Energy demand (GW per t/h) per input carrier of a production technology:
        the fuel above 200 °C of the energy intensity `energy` split by the fuel
        shares `fuel_inputs`, the electricity and the heat bands with demand."""
        heat = self.calculate_heat_conversion_factors(sector, energy)
        heat = heat[heat > 0].add_prefix("heat_industry_")
        electricity = pd.Series({"electricity": energy["electricity"]})
        return pd.concat([energy["fuel"] * fuel_inputs, electricity, heat]).round(12)

    @cached_property
    def reference_boiler_efficiency(self) -> float:
        """Useful heat per final energy below 200 °C: Rehfeldt et al. (2017) report
        final energy, converted with the mean efficiency of the DEA industrial
        boilers."""
        return cast(DEA, self.data["dea"]).get_mean_efficiency_industry_boilers()

    # ---------- fuel mix ----------

    def calculate_fuel_shares(self, sector: str) -> pd.Series:
        """Fuel mix of the sector's thermal energy (JRC-IDEES, EU27), fuels below
        the cut-off dropped."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        thermal = idees.get_industry_thermal_final_energy_by_fuel(
            sector, DATA_YEAR, "production"
        ).loc[IDEES_EU]
        shares = (thermal / thermal.sum()).drop("other", errors="ignore")
        shares = shares[shares >= FUEL_SHARE_CUTOFF]
        return shares / shares.sum()

    @staticmethod
    def calculate_fuel_inputs_kiln(sector: str) -> pd.Series:
        """Fuel shares of a kiln- or furnace-fired sector: all its fuel is the
        sector's kiln or furnace fuel, supplied by the fuel retrofits."""
        return pd.Series({f"{sector}_fuel": 1.0})

    # ---------- production and capacity ----------

    @cached_property
    def capacity_utilisation(self) -> float:
        """Physical output per installed capacity where no capacity data exist."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        return idees.get_industry_capacity_utilisation(CAPACITY_DATA_SECTORS, DATA_YEAR)

    def get_industry_physical_output(
        self, sector: str, nodes: tuple[str, ...]
    ) -> pd.Series:
        """JRC-IDEES physical output (kt/a) of a sector at the model nodes."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        return self.reindex_nodes(
            idees.get_industry_physical_output(sector, DATA_YEAR), nodes
        )

    def get_industry_installed_capacity(
        self, sector: str, nodes: tuple[str, ...]
    ) -> pd.Series:
        """JRC-IDEES installed capacity (kt/a) of a sector at the model nodes."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        return self.reindex_nodes(
            idees.get_industry_installed_capacity(sector, DATA_YEAR), nodes
        )

    def get_industry_thermal_final_energy(
        self, sector: str, nodes: tuple[str, ...]
    ) -> pd.Series:
        """JRC-IDEES thermal final energy (ktoe) of a sector at the model nodes."""
        idees = cast(JRCIDEES, self.data["jrc_idees"])
        thermal = idees.get_industry_thermal_final_energy(sector, DATA_YEAR)
        return self.reindex_nodes(thermal.sum(axis=1), nodes)

    @staticmethod
    def to_t_per_hour(data: ProductionT) -> ProductionT:
        """Convert a production from kt/a to t/h."""
        return data * 1000.0 / Constants.HOURS_PER_YEAR

    @staticmethod
    def reindex_nodes(data: pd.Series, nodes: tuple[str, ...]) -> pd.Series:
        """Select the model nodes; nodes without data are 0."""
        return data.reindex(list(nodes), fill_value=0.0)

    def fill_proxy_nodes(self, data: pd.Series) -> pd.Series:
        """Fill the nodes without JRC-IDEES data from their proxy node, scaled by
        the population ratio for the nodes in POPULATION_SCALED."""
        data = data.copy()
        for node, proxy in PROXY_NODES.items():
            data[node] = data[proxy] * self._proxy_factor(node, proxy)
        return data

    # ---------- lifetime and costs ----------

    def get_lifetime(
        self,
        element: Element,
        processes: dict[str, str],
        weights: pd.Series,
        description: str,
    ) -> Attribute:
        """Get the lifetime of a production technology: the JRC-EU-TIMES lifetime of
        the `processes` of a sector's sub-processes, weighted by `weights`."""
        times = cast(JRCEUTIMESIndustry, self.data["jrc_eu_times_industry"])
        lifetimes = pd.Series(
            {
                sub_process: times.get_process_parameters(process)["LIFE"]
                for sub_process, process in processes.items()
            }
        )
        return element.lifetime.set_data(
            default_value=float(round(lifetimes.dot(weights[lifetimes.index]))),
            source=SourceInformation(description=description, metadata=self.metadata),
        )

    def get_no_cost(self, attribute: Attribute) -> Attribute:
        """Set a cost of a production technology to 0: its capacity follows the
        fixed product demand and no other route produces the product, so its cost
        would only add a constant to the objective."""
        return attribute.set_data(
            default_value=0.0,
            source=AssumptionInformation(
                description=(
                    "Not modeled: the production capacity follows the fixed product "
                    "demand and no other technology produces the product, so the "
                    "cost would only add a constant to the objective and change no "
                    "decision. See docs, 'Production technologies'."
                )
            ),
        )

    # ---------- helpers ----------

    def _proxy_factor(self, node: str, proxy: str) -> float:
        """Population of `node` per population of `proxy` (World Bank)."""
        worldbank = cast(WorldBankPopulation, self.data["worldbank_population"])
        population = worldbank.get_population([node, proxy], [DATA_YEAR])[DATA_YEAR]
        return float(population[node] / population[proxy])
