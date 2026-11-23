from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import SourceInformation

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.datasets.datasets.carrier.ipcc_emission_factors import (
    IPCCEmissionFactors,
)
from zen_europe.datasets.datasets.carrier.rehfeldt2017 import Rehfeldt2017
from zen_europe.datasets.datasets.technology.cerame_unie2021 import CerameUnie2021
from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import instance_cache

if TYPE_CHECKING:
    from zen_creator import (
        Carrier,
        ConversionTechnology,
        Dataset,
        RetrofittingTechnology,
    )
    from zen_creator.utils.settings import Settings

SECTOR = "ceramic"
# JRC-EU-TIMES process whose lifetime is used: gas-fired process heat of non-metallic
# minerals, as JRC-EU-TIMES has no ceramic process
JRC_PROCESS = "INMPRCGAS01"
# natural gas, today's fuel of all ceramic kilns, can cover the whole ceramic fuel
NATURAL_GAS_MAX_SHARE = 1.0


class CeramicProductionData(DatasetCollection):
    """Ceramic production: demand, energy intensity, capacity, lifetime, process CO2
    and the fuel of the ceramic kilns."""

    name = "ceramic_production_data"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "industry_production_data": IndustryProductionData(
                self.settings, self.source_path
            ),
            "rehfeldt2017": Rehfeldt2017(self.source_path),
            "ipcc_emission_factors": IPCCEmissionFactors(self.source_path),
            "cerame_unie2021": CerameUnie2021(self.source_path),
        }

    # ---------- product ----------

    def get_demand(self, element: Carrier) -> Attribute:
        """Get the ceramic demand: today's production."""
        return self._industry.get_demand(
            element,
            self.calculate_production(tuple(element.model.config.system.set_nodes)),
            "The production is the JRC-IDEES thermal energy consumption divided by "
            "the Rehfeldt et al. (2017) fuel intensity; CH, NO and UK use a proxy "
            "node (CH as AT, NO as FI, UK as DE scaled by the World Bank "
            "population).",
        )

    # ---------- production technology ----------

    def get_input_carrier(self, element: ConversionTechnology) -> Attribute:
        """Get the input carriers of ceramic production."""
        return self._industry.get_input_carrier(
            element,
            self.calculate_conversion_factors(),
            "The ceramic kilns are fired with natural gas today, supplied as ceramic "
            "fuel; its fuel switching is modeled by the ceramic fuel retrofits.",
        )

    def get_conversion_factor(self, element: ConversionTechnology) -> Attribute:
        """Get the energy demand per tonne of ceramic."""
        return self._industry.get_conversion_factor(
            element,
            self.calculate_conversion_factors(),
            "The energy intensity is the activity-weighted energy intensity of the "
            "ceramic sub-processes from Rehfeldt et al. (2017); the fuel above "
            "200 °C is supplied as ceramic fuel.",
        )

    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """Get the existing ceramic production capacity."""
        industry = self._industry
        return industry.get_capacity_existing(
            element,
            self.calculate_production(tuple(element.model.config.system.set_nodes))
            / industry.capacity_utilisation,
            "The existing production capacity is the production divided by "
            f"{industry.describe_capacity_utilisation()}.",
        )

    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """Get the lifetime of the JRC-EU-TIMES proxy process."""
        return self._industry.get_lifetime(
            element,
            {SECTOR: JRC_PROCESS},
            pd.Series({SECTOR: 1.0}),
            "JRC-EU-TIMES has no ceramic process; the lifetime of its gas-fired "
            f"process heat of non-metallic minerals ({JRC_PROCESS}) is used.",
        )

    def get_carbon_intensity_technology(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the process CO2 of ceramic production."""
        intensity = self.calculate_process_emissions()
        return element.carbon_intensity_technology.set_data(
            default_value=round(intensity, 12),
            unit="ton/tproduct",
            source=SourceInformation(
                description=(
                    "The process CO2 emissions of ceramic production are "
                    f"{intensity:.4f} t per t of ceramic: the combustion emissions "
                    f"of {self._fuel_total:.3f} GJ/t (Rehfeldt et al. (2017)) x "
                    f"{self._calculate_combustion_emission_factor():.4f} t/GJ "
                    "(natural gas, IPCC emission factor), times the process per "
                    "fuel combustion emissions of the European ceramic industry in "
                    "2020 (17 % process, 64 % fuel combustion and 19 % indirect "
                    "emissions; Cerame-Unie (2021), Ceramic Roadmap to 2050, p. 30). "
                    "See docs, 'Production technologies'."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- post-combustion capture ----------

    def get_conversion_factor_post_comb(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the conversion factor of ceramic_post_comb."""
        return self._industry.get_conversion_factor_post_comb(
            element, self.calculate_fuel_shares()
        )

    def get_retrofit_flow_coupling_factor_post_comb(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the captured process CO2 per tonne of ceramic."""
        return self._industry.get_retrofit_flow_coupling_factor_post_comb(
            element, self.calculate_process_emissions()
        )

    # ---------- ceramic fuel retrofits ----------

    def get_retrofit_flow_coupling_factor_natural_gas(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the ceramic fuel natural_gas_to_ceramic_fuel supplies at most per
        tonne of ceramic: the whole ceramic fuel demand."""
        return self._industry.get_retrofit_flow_coupling_factor_fuel(
            element,
            NATURAL_GAS_MAX_SHARE,
            self.calculate_conversion_factors()[f"{SECTOR}_fuel"],
            "natural gas is today's fuel of all ceramic kilns",
        )

    def get_retrofit_flow_coupling_factor_switchable(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the ceramic fuel a switching retrofit (hydrogen, electricity) supplies
        at most per tonne of ceramic: the switchable share of the ceramic fuel
        demand."""
        return self._industry.get_retrofit_flow_coupling_factor_fuel(
            element,
            self._switchable_share,
            self.calculate_conversion_factors()[f"{SECTOR}_fuel"],
            "the ceramic BREF (JRC, Final Draft, April 2026, Sections 4.2.1-4.2.3) "
            "limits electrified kilns to below 1600 °C; the > 1000 °C fuel of "
            "technical ceramics in Rehfeldt et al. (2017) is treated as not "
            "switchable and stays natural gas",
        )

    # ---------- data used by other collections ----------

    @instance_cache
    def calculate_production(self, nodes: tuple[str, ...]) -> pd.Series:
        """Physical production (t/h): JRC-IDEES thermal energy / Rehfeldt fuel
        intensity, proxy nodes filled."""
        industry = self._industry
        thermal = industry.get_industry_thermal_final_energy(SECTOR, nodes)  # ktoe
        output = thermal * Constants.GJ_PER_KTOE / (self._fuel_total * 1000)  # kt/a
        return industry.to_t_per_hour(industry.fill_proxy_nodes(output))

    def calculate_demand(self, nodes: tuple[str, ...]) -> pd.Series:
        """Ceramic demand (t/h): the physical production."""
        return self.calculate_production(nodes).rename("demand").rename_axis("node")

    def calculate_energy_intensity(self) -> pd.Series:
        """Fuel (above 200 °C), heat and electricity demand (GW per t/h) from the
        Rehfeldt et al. (2017) sub-processes."""
        return self._energy_intensity

    def calculate_heat_conversion_factors(self) -> pd.Series:
        """Heat demand per band (GW per t/h)."""
        return self._industry.calculate_heat_conversion_factors(
            SECTOR, self.calculate_energy_intensity()
        )

    def calculate_fuel_shares(self) -> pd.Series:
        """Fuel mix: natural gas, today's fuel of all ceramic kilns."""
        return pd.Series({"natural_gas": 1.0})

    def calculate_conversion_factors(self) -> pd.Series:
        """Energy demand (GW per t/h) per input carrier."""
        return self._industry.calculate_conversion_factors(
            SECTOR, self.calculate_energy_intensity(), self._calculate_fuel_inputs()
        )

    def calculate_process_emissions(self) -> float:
        """Process CO2 of ceramic production (t per t of ceramic): the combustion
        emissions times the process per combustion emissions of Cerame-Unie."""
        cerame_unie = cast(CerameUnie2021, self.data["cerame_unie2021"])
        combustion = self._fuel_total * self._calculate_combustion_emission_factor()
        return combustion * cerame_unie.get_process_per_combustion_emissions()

    # ---------- helpers ----------

    @property
    def _industry(self) -> IndustryProductionData:
        return cast(IndustryProductionData, self.data["industry_production_data"])

    @cached_property
    def _energy_intensity(self) -> pd.Series:
        return self._industry.calculate_energy_intensity_rehfeldt(SECTOR)

    @cached_property
    def _fuel_total(self) -> float:
        """Total fuel intensity (GJ/t) of the Rehfeldt et al. (2017) sub-processes."""
        return self._industry.calculate_fuel_total_rehfeldt(SECTOR)

    @property
    def _switchable_share(self) -> float:
        """Share of the ceramic fuel that can switch to hydrogen or electricity
        (Rehfeldt)."""
        rehfeldt = cast(Rehfeldt2017, self.data["rehfeldt2017"])
        return rehfeldt.get_switchable_share_ceramic()

    def _calculate_combustion_emission_factor(self) -> float:
        """CO2 per GJ of fuel (t/GJ) of the ceramic JRC-IDEES fuel mix with the IPCC
        emission factors; biomass is carbon-neutral."""
        ipcc = cast(IPCCEmissionFactors, self.data["ipcc_emission_factors"])
        return sum(
            fuel_share * ipcc.get_emission_factor(str(carrier)) / Constants.GJ_PER_MWH
            for carrier, fuel_share in self.calculate_fuel_shares().items()
        )

    def _calculate_fuel_inputs(self) -> pd.Series:
        """All fuel is ceramic fuel."""
        return self._industry.calculate_fuel_inputs_kiln(SECTOR)
