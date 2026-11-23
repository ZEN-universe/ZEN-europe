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
from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.utils.utils import instance_cache

if TYPE_CHECKING:
    from zen_creator import (
        Carrier,
        ConversionTechnology,
        Dataset,
        RetrofittingTechnology,
    )
    from zen_creator.utils.settings import Settings

SECTOR = "glass"
# JRC-EU-TIMES processes of the glass routes
JRC_PROCESSES = {
    "container": "IGHHOLLOW01",
    "flat": "IGFFLATGL01",
    "fibre": "IGFFLATGL01",
}


class GlassProductionData(DatasetCollection):
    """Glass production: demand, energy intensity, capacity, lifetime, process CO2
    and the fuel of the glass furnaces."""

    name = "glass_production_data"

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
            "aidres": Aidres(self.source_path),
        }

    # ---------- product ----------

    def get_demand(self, element: Carrier) -> Attribute:
        """Get the glass demand: today's production."""
        return self._industry.get_demand(
            element,
            self.calculate_production(tuple(element.model.config.system.set_nodes)),
            "The production is the JRC-IDEES physical output; CH, NO and UK use a "
            "proxy node (CH as AT, NO as FI, UK as DE scaled by the World Bank "
            "population).",
        )

    # ---------- production technology ----------

    def get_input_carrier(self, element: ConversionTechnology) -> Attribute:
        """Get the input carriers of glass production."""
        return self._industry.get_input_carrier(
            element,
            self.calculate_conversion_factors(),
            "Glass is fired with natural gas, the AIDRES (2023) reference route, "
            "supplied as glass fuel.",
        )

    def get_conversion_factor(self, element: ConversionTechnology) -> Attribute:
        """Get the energy demand per tonne of glass."""
        return self._industry.get_conversion_factor(
            element,
            self.calculate_conversion_factors(),
            "The energy intensity is that of the AIDRES (2023) natural gas routes, "
            "weighted by EU production share; the fuel is supplied as glass fuel.",
        )

    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """Get the existing glass production capacity."""
        return self._industry.get_capacity_existing(
            element,
            self._calculate_capacity(tuple(element.model.config.system.set_nodes)),
            "The existing production capacity is the JRC-IDEES installed capacity "
            "at 8760 hours per year; CH, NO and UK use a proxy node.",
        )

    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """Get the lifetime from JRC-EU-TIMES."""
        aidres = cast(Aidres, self.data["aidres"])
        return self._industry.get_lifetime(
            element,
            JRC_PROCESSES,
            aidres.get_production_shares_glass(),
            "JRC-EU-TIMES lifetime of the glass processes, weighted by the AIDRES "
            "(2023) EU production shares of the glass routes.",
        )

    def get_carbon_intensity_technology(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the process CO2 of glass production."""
        intensity = self.calculate_process_emissions()
        return element.carbon_intensity_technology.set_data(
            default_value=round(intensity, 12),
            unit="ton/tproduct",
            source=SourceInformation(
                description=(
                    "The process CO2 emissions of glass production are "
                    f"{intensity:.4f} t per t of glass: the direct emissions of the "
                    "electric glass routes, which only emit process CO2, weighted by "
                    "EU production share (AIDRES (2023), Tables 19, 21 and 23). See "
                    "docs, 'Production technologies'."
                ),
                metadata=self.metadata,
            ),
        )

    # ---------- post-combustion capture ----------

    def get_conversion_factor_post_comb(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the conversion factor of glass_post_comb."""
        return self._industry.get_conversion_factor_post_comb(
            element, self.calculate_fuel_shares()
        )

    def get_retrofit_flow_coupling_factor_post_comb(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the captured process CO2 per tonne of glass."""
        return self._industry.get_retrofit_flow_coupling_factor_post_comb(
            element, self.calculate_process_emissions()
        )

    # ---------- glass fuel retrofits ----------

    def get_retrofit_flow_coupling_factor_fuel(
        self, element: RetrofittingTechnology
    ) -> Attribute:
        """Get the glass fuel a glass fuel retrofit supplies at most per tonne of
        glass: the fuel's maximum share times the glass fuel demand."""
        aidres = cast(Aidres, self.data["aidres"])
        return self._industry.get_retrofit_flow_coupling_factor_fuel(
            element,
            aidres.get_max_fuel_share_glass(element.name),
            self.calculate_conversion_factors()[f"{SECTOR}_fuel"],
            "AIDRES (2023): the glass routes run fully on natural gas, hydrogen or "
            "electricity",
        )

    # ---------- data used by other collections ----------

    @instance_cache
    def calculate_production(self, nodes: tuple[str, ...]) -> pd.Series:
        """Physical production (t/h): the JRC-IDEES physical output, proxy nodes
        filled."""
        industry = self._industry
        output = industry.get_industry_physical_output(SECTOR, nodes)
        return industry.to_t_per_hour(industry.fill_proxy_nodes(output))

    def calculate_demand(self, nodes: tuple[str, ...]) -> pd.Series:
        """Glass demand (t/h): the physical production."""
        return self.calculate_production(nodes).rename("demand").rename_axis("node")

    @cached_property
    def _energy_intensity(self) -> pd.Series:
        aidres = cast(Aidres, self.data["aidres"])
        routes = aidres.get_sub_processes_glass()
        weights = aidres.get_production_shares_glass()
        return self._industry.calculate_energy_intensity(
            SECTOR,
            float(weights.dot(routes.loc[weights.index, "ng_GJ_t"])),
            float(weights.dot(routes.loc[weights.index, "elec_GJ_t"])),
            weights,
        )

    def calculate_energy_intensity(self) -> pd.Series:
        """Fuel (above 200 °C), heat and electricity demand (GW per t/h) of the
        AIDRES natural gas routes, weighted by EU production share."""
        return self._energy_intensity

    def calculate_heat_conversion_factors(self) -> pd.Series:
        """Heat demand per band (GW per t/h)."""
        return self._industry.calculate_heat_conversion_factors(
            SECTOR, self.calculate_energy_intensity()
        )

    def calculate_fuel_shares(self) -> pd.Series:
        """Fuel mix: natural gas, the AIDRES reference route."""
        return pd.Series({"natural_gas": 1.0})

    def calculate_conversion_factors(self) -> pd.Series:
        """Energy demand (GW per t/h) per input carrier."""
        return self._industry.calculate_conversion_factors(
            SECTOR, self.calculate_energy_intensity(), self._calculate_fuel_inputs()
        )

    def calculate_process_emissions(self) -> float:
        """Process CO2 of glass production (t per t of glass) from AIDRES."""
        return cast(Aidres, self.data["aidres"]).get_process_emissions_glass()

    # ---------- helpers ----------

    @property
    def _industry(self) -> IndustryProductionData:
        return cast(IndustryProductionData, self.data["industry_production_data"])

    def _calculate_fuel_inputs(self) -> pd.Series:
        """All fuel is glass fuel."""
        return self._industry.calculate_fuel_inputs_kiln(SECTOR)

    @instance_cache
    def _calculate_capacity(self, nodes: tuple[str, ...]) -> pd.Series:
        """Installed capacity (t/h): JRC-IDEES, proxy nodes filled."""
        industry = self._industry
        capacity = industry.get_industry_installed_capacity(SECTOR, nodes)
        return industry.to_t_per_hour(industry.fill_proxy_nodes(capacity))
