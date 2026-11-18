from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator import Attribute, EnergySystem, SourceInformation, Technology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class TechnologyDiffusionMannhardt(Dataset[dict[str, pd.DataFrame]]):
    """
    Maximum technology diffusion rates, based on Mannhardt et al. (2024).

    Technologies are grouped into four categories. Each category takes the
    historically observed diffusion rate of one reference technology.

    The regression of the historical diffusion also yields the knowledge
    spillover rate between the nodes and the market share that is exempt from
    the diffusion limit, which are properties of the energy system rather than
    of a single technology.
    """

    name = "technology_diffusion_mannhardt"

    # diffusion rate per category and the reference technology it is derived from
    DIFFUSION_RATES = {
        "LOW": 0.1,
        "MEDIUM": 0.13,
        "HIGH": 0.29,
        "VERY_HIGH": 0.4,
    }
    # knowledge spillover rate per knowledge depreciation rate
    SPILLOVER_RATES = {
        0.1: 0.07,
        0.2: 0.056,
    }
    # market share that is exempt from the diffusion limit
    MARKET_SHARE_UNBOUNDED = 0.02
    REFERENCE_TECHNOLOGIES = {
        "LOW": "wind offshore",
        "MEDIUM": "wind onshore",
        "HIGH": "photovoltaics",
        "VERY_HIGH": "battery electric vehicles",
    }

    LOW = [
        "hard_coal_plant",
        "nuclear",
        "reservoir_hydro",
        "wind_offshore",
        "lignite_coal_plant",
        "pumped_hydro",
        "hydrogen_storage",
        "natural_gas_storage",
    ]
    MEDIUM = [
        "wind_onshore",
        "natural_gas_turbine",
        "hard_coal_plant_CCS",
        "natural_gas_turbine_CCS",
        "run-of-river_hydro",
        "biomass_plant",
        "biomass_plant_CCS",
        "oil_plant",
        "waste_plant",
        "lng_terminal",
        "natural_gas_boiler_DH",
        "heat_pump_DH",
        "oil_boiler_DH",
        "waste_boiler_DH",
        "biomass_boiler_DH",
        "hard_coal_boiler_DH",
        "electrode_boiler_DH",
        "district_heating_grid",
        "electrolysis",
        "fuel_cell",
        "gasification",
        "gasification_CCS",
        "SMR",
        "SMR_CCS",
        "biomethane_conversion",
        "power_line",
        "natural_gas_pipeline",
        "carbon_pipeline",
        "hydrogen_pipeline",
        "coal_to_cement_fuel",
        "biomass_to_cement_fuel",
        "waste_to_cement_fuel",
        "hydrogen_to_cement_fuel",
        "olefin_from_methanol",
        "diesel_ICE_ship",
        "ammonia_ICE_ship",
        "methanol_ICE_ship",
        "hydrogen_ICE_ship",
        "hydrogen_FC_ship",
        "BF_BOF",
        "NG_DRI",
        "H2_DRI",
        "carbon_storage",
        "BF_BOF_CCS",
        "NG_DRI_CCS",
        "cement_post_comb",
        "methanol_from_natural_gas",
        "methanol_from_hydrogen",
        "methanol_from_biomass",
        "fischer_tropsch",
        "DAC",
        "pyrolysis",
        "refining",
        "methanation",
        "oil_to_gasoline_conversion",
        "oil_to_diesel_conversion",
        "oil_to_kerosene_conversion",
    ]
    HIGH = [
        "photovoltaics",
        "natural_gas_boiler",
        "heat_pump",
        "oil_boiler",
        "biomass_boiler",
        "hard_coal_boiler",
        "electrode_boiler",
        "battery",
        "HDT_BET",
        "HDT_diesel",
        "HDT_FCEV",
    ]
    VERY_HIGH = [
        "BEV",
        "ICE_diesel",
        "ICE_petrol",
        "HEV",
        "PHEV",
        "ICE_cng",
    ]

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self.categories = {
            technology: category
            for category in self.DIFFUSION_RATES
            for technology in getattr(self, category)
        }

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Understanding the vicious cycle of myopic foresight and "
                "constrained technology deployment in transforming the "
                "European energy system"
            ),
            author=["Jacob Mannhardt", "Paolo Gabrielli", "Giovanni Sansavini"],
            publication="iScience",
            publication_year=2024,
            url="https://www.cell.com/iscience/fulltext/S2589-0042(24)02594-X",
            doi="https://doi.org/10.1016/j.isci.2024.111369",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        """
        No data to be set.
        """
        data: dict[str, pd.DataFrame] = {}
        return data

    # -------- methods ------------------------
    def get_category(
        self, technology: Technology, proxy_element_name: str | None = None
    ) -> str:
        """
        Get the diffusion category of a technology, or of its proxy technology.
        """
        technology_name = proxy_element_name or technology.name
        if technology_name not in self.categories:
            raise ValueError(
                f"No diffusion rate is available for technology '{technology_name}'."
            )
        return self.categories[technology_name]

    def get_max_diffusion_rate(
        self, technology: Technology, proxy_element_name: str | None = None
    ) -> Attribute:
        """
        Get the maximum diffusion rate of a technology.

        With `proxy_element_name`, the technology diffuses as the proxy technology.
        """
        category = self.get_category(technology, proxy_element_name)
        proxy = f" (as {proxy_element_name})" if proxy_element_name else ""
        attr = technology.max_diffusion_rate
        attr.set_data(
            default_value=self.DIFFUSION_RATES[category],
            unit="1",
            source=SourceInformation(
                description=(
                    f"The maximum diffusion rate of {technology.name}{proxy} is set "
                    f"to the historically observed diffusion rate of "
                    f"{self.REFERENCE_TECHNOLOGIES[category]} from Mannhardt "
                    f"et al. (2024)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_knowledge_depreciation_rate(self, element: EnergySystem) -> Attribute:
        """
        Get the knowledge depreciation rate of the energy system.

        The diffusion rates are regressed under the assumption of one of the
        depreciation rates of the study, which is selected with
        settings.investment.knowledge_depreciation_rate.
        """
        depreciation_rate = self._get_depreciation_rate(element)
        attr = element.knowledge_depreciation_rate
        return attr.set_data(
            default_value=depreciation_rate,
            unit="1",
            source=SourceInformation(
                description=(
                    f"The knowledge depreciation rate is {depreciation_rate}, "
                    f"one of the rates Mannhardt et al. (2024) assume when "
                    f"they regress the diffusion rates."
                ),
                metadata=self.metadata,
            ),
        )

    def get_knowledge_spillover_rate(self, element: EnergySystem) -> Attribute:
        """
        Get the knowledge spillover rate between the nodes.

        The rate belongs to the knowledge depreciation rate the diffusion
        rates were regressed with.
        """
        depreciation_rate = self._get_depreciation_rate(element)
        attr = element.knowledge_spillover_rate
        return attr.set_data(
            default_value=self.SPILLOVER_RATES[depreciation_rate],
            unit="1",
            source=SourceInformation(
                description=(
                    f"The knowledge spillover rate between the nodes is the "
                    f"rate that Mannhardt et al. (2024) regress together with "
                    f"the diffusion rates, for a knowledge depreciation rate "
                    f"of {depreciation_rate}."
                ),
                metadata=self.metadata,
            ),
        )

    def _get_depreciation_rate(self, element: EnergySystem) -> float:
        """
        Get the knowledge depreciation rate the study is evaluated for.
        """
        depreciation_rate = element.settings.investment.knowledge_depreciation_rate
        if depreciation_rate not in self.SPILLOVER_RATES:
            raise ValueError(
                f"Mannhardt et al. (2024) do not assume a knowledge "
                f"depreciation rate of {depreciation_rate}."
            )
        return depreciation_rate

    def get_market_share_unbounded(self, element: EnergySystem) -> Attribute:
        """
        Get the market share that is exempt from the diffusion limit.
        """
        attr = element.market_share_unbounded
        return attr.set_data(
            default_value=self.MARKET_SHARE_UNBOUNDED,
            unit="1",
            source=SourceInformation(
                description=(
                    "The market share that is exempt from the diffusion limit "
                    "is taken from Mannhardt et al. (2024)."
                ),
                metadata=self.metadata,
            ),
        )
