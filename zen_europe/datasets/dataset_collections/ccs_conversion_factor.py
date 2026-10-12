from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.ipcc_emission_factors import (
    IPCCEmissionFactors,
)
from zen_europe.datasets.datasets.financial.dea import DEA

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset


from zen_creator import (
    Attribute,
    ConversionTechnology,
    DatasetCollection,
    RetrofittingTechnology,
    SourceInformation,
)
from zen_creator.utils.settings import Settings


class CCSConversionFactor(DatasetCollection):
    """
    Calculating the conversion factor for carbon capture and storage (CCS) technologies.
    """

    name = "ccs_conversion_factor"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "dea": DEA(self.source_path),
            "technology_cost_database": TechnologyCostDatabase(
                self.settings, self.source_path
            ),
            "ipcc_emission_factors": IPCCEmissionFactors(self.source_path),
        }

    def get_conversion_factor_CCS(
        self, element: RetrofittingTechnology, base_tech: ConversionTechnology
    ) -> Attribute:
        r"""
        Get the conversion factor for CCS technologies in the electricity sector.

        This function retrieves the conversion factor for electricity produced by
        CCS technologies for the specified element.

        The electricity per input unit fuel is the difference in efficiency between
        the base technology (:math:`\eta_{base}`) and the CCS technology
        (:math:`\eta_{ccs}`). The electricity per unit of
        sequestered carbon is the delta in efficiency divided by the carbon intensity
        of the input fuel (:math:`CI`) and the capture rate of the CCS technology
        (:math:`CR`): :math:`\frac{\eta_{base} - \eta_{ccs}}{CI * CR}`
        """
        tech_db = cast(TechnologyCostDatabase, self.data["technology_cost_database"])
        ipcc_emission_factors = cast(
            IPCCEmissionFactors, self.data["ipcc_emission_factors"]
        )
        eff_base, agencies_base = tech_db.get_efficiency(element=base_tech)
        eff_ccs, agencies_ccs = tech_db.get_efficiency(element=element)
        carbon_removal_factor = self.get_carbon_removal_factor(
            element=base_tech, conversion_factor=1 / eff_base.iloc[0]
        )
        carbon_removal_potential_withCCS = self.get_carbon_removal_factor(
            element=base_tech, conversion_factor=1 / eff_ccs.iloc[0]
        )
        conversion_factor = (
            1 / carbon_removal_factor - 1 / carbon_removal_potential_withCCS
        )
        unit = ipcc_emission_factors.get_unit()
        if unit == "tons/MWh":
            inverted_unit = "MWh/tCO2"
        else:
            raise ValueError(f"Unexpected unit for carbon intensity: {unit}")
        attr = element.conversion_factor
        conversion_factors = [
            {"electricity": {"default_value": conversion_factor, "unit": inverted_unit}}
        ]
        return attr.set_data(
            default_value=conversion_factors,
            source=SourceInformation(
                description=(
                    "The conversion factor for CCS technologies is calculated as the "
                    "difference in efficiency between the base technology and the CCS "
                    "technology, divided by the carbon intensity of the input fuel and "
                    "the capture rate of the CCS technology. This factor represents "
                    "the amount of extra electricity required per unit of sequestered "
                    "carbon."
                ),
                metadata=self.metadata,
            ),
        )

    def get_carbon_removal_factor(
        self, element: ConversionTechnology, conversion_factor: float
    ) -> float:
        """
        Get the carbon removal factor for CCS technologies.

        This function retrieves the carbon removal factor for the specified element.
        """
        dea = cast(DEA, self.data["dea"])
        ipcc_emission_factors = cast(
            IPCCEmissionFactors, self.data["ipcc_emission_factors"]
        )

        input_carriers = cast(list[str], element.input_carrier.default_value)
        assert len(input_carriers) == 1, (
            "For now, " "CCS technology must have exactly one input carrier."
        )
        fuel = element.model.carriers[input_carriers[0]]
        carbon_intensity = ipcc_emission_factors._get_raw_carbon_intensity(fuel)
        capture_rate = dea.get_capture_rate_CCS()
        carbon_removal_factor = carbon_intensity * capture_rate * conversion_factor
        return carbon_removal_factor

    def get_retrofit_flow_coupling_factor(
        self, element: RetrofittingTechnology, base_tech: ConversionTechnology
    ) -> Attribute:
        """
        Get the retrofit flow coupling factor for CCS technologies.

        This function retrieves the retrofit flow coupling factor for the specified
        element.
        """
        tech_db = cast(TechnologyCostDatabase, self.data["technology_cost_database"])
        eff_ccs, agencies_ccs = tech_db.get_efficiency(element=element)
        carbon_removal_factor = self.get_carbon_removal_factor(
            element=base_tech, conversion_factor=1 / eff_ccs.iloc[0]
        )
        ipcc_emission_factors = cast(
            IPCCEmissionFactors, self.data["ipcc_emission_factors"]
        )
        unit = ipcc_emission_factors.get_unit()
        if unit == "tons/MWh":
            unit = "tCO2/MWh"
        else:
            raise ValueError(f"Unexpected unit for carbon intensity: {unit}")
        attr = element.retrofit_flow_coupling_factor
        return attr.set_data(
            default_value=carbon_removal_factor,
            unit=unit,
            source=SourceInformation(
                description=(
                    "The retrofit flow coupling factor of CCS technologies is "
                    "calculated as the product of the carbon intensity of the "
                    "input fuel, the capture rate of the CCS technology, and "
                    f"the inverse of the combined base + ccs technology's efficiency "
                    f"(from {agencies_ccs}). This "
                    "factor represents the amount of CO2 captured per unit of "
                    "fuel input."
                ),
                metadata=self.metadata,
            ),
        )

    def get_retrofit_flow_coupling_factor_SMR_CCS(
        self, element: RetrofittingTechnology, base_tech: ConversionTechnology
    ) -> Attribute:
        """
        Get the retrofit flow coupling factor for SMR CCS technology.
        """
        conversion_factors = cast(
            list[dict[str, dict[str, float]]], base_tech.conversion_factor.default_value
        )
        conversion_factor = conversion_factors[0]["natural_gas"]["default_value"]
        carbon_removal_factor = self.get_carbon_removal_factor(
            element=base_tech, conversion_factor=conversion_factor
        )
        attr = element.retrofit_flow_coupling_factor
        return attr.set_data(
            default_value=carbon_removal_factor,
            unit="tCO2/MWh",
            source=SourceInformation(
                description=(
                    "The retrofit flow coupling factor of SMR CCS technology is "
                    "calculated as the product of the carbon intensity of natural gas, "
                    "the capture rate of the CCS technology, and "
                    "the efficiency of the SMR technology. "
                ),
                metadata=self.metadata,
            ),
        )
