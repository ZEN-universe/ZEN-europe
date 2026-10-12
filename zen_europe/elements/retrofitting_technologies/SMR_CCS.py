from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.ccs_conversion_factor import (
    CCSConversionFactor,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.IOGP_carbon_storage_projects import (
    IOGPCarbonStorageProjects,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    RetrofittingTechnology,
    SourceInformation,
)


class SMR_CCS(RetrofittingTechnology):
    """Class containing all data and assumptions for steam methane
    reforming (SMR) retrofitted with post-combustion carbon capture (CCS)."""

    name: str = "SMR_CCS"
    base_technology_name: str = "SMR"

    def __init__(self, model: Model, power_unit: str = "tCO2/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of SMR CCS to carbon.
        """
        return Attribute(
            name="reference_carrier", default_value=["carbon"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of SMR CCS to natural gas and electricity.
        """
        return Attribute(
            name="input_carrier",
            default_value=["natural_gas", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of SMR CCS to carbon.
        """
        return Attribute(name="output_carrier", default_value=["carbon"], element=self)

    def _set_retrofit_reference_carrier(self) -> Attribute:
        """
        Sets the retrofit reference carrier of SMR CCS to carbon.
        """
        return Attribute(
            name="retrofit_reference_carrier", default_value=["carbon"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of SMR CCS.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of SMR CCS.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of SMR CCS.

        Values from the DEA technology catalogue for carbon capture,
        transport and storage (Post-combustion carbon capture retrofit -
        100 MW(th) WtE or biomass CHP plant, used as a proxy entry),
        assuming all heat demand for the capture process is supplied from
        natural gas.
        https://ens.dk/en/our-services/projections-and-models/technology-data/technology-data-carbon-capture-transport-and
        """
        attr = self.conversion_factor
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_SMR_CCS()
        source = SourceInformation(
            description=(
                "The conversion factor of SMR CCS is a manually derived "
                "value based on the DEA technology catalogue for carbon "
                "capture, transport and storage (Post-combustion carbon "
                "capture retrofit - 100 MW(th) WtE or biomass CHP plant, "
                "used as a proxy entry, assuming all heat demand is "
                "supplied from natural gas)."
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for SMR CCS.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for SMR CCS.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for
        SMR CCS.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        """
        Return the retrofit flow coupling factor of SMR CCS.

        This factor represents the amount of CO2 captured per unit of SMR CCS output.
        """
        ccs_cf = CCSConversionFactor(
            settings=self.settings, source_path=self.source_path
        )
        base_tech = self.model.elements[self.base_technology_name]
        return ccs_cf.get_retrofit_flow_coupling_factor_SMR_CCS(
            element=self, base_tech=base_tech
        )

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of SMR CCS.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            igop_projects = IOGPCarbonStorageProjects(source_path=self.source_path)
            return igop_projects.get_capacity_existing_capture(self)
        else:
            attr = self.capacity_existing
            attr.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description=("We do not consider existing capacities."),
                ),
            )
            return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of SMR CCS.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

    def _set_capacity_addition_unbounded(self) -> Attribute:
        """
        Sets the unbounded capacity addition of SMR CCS.

        Capacity additions up to the size of a single reference project are
        exempt from the diffusion limit, so that a first plant can be built
        from a zero installed base.
        """
        attr = self.capacity_addition_unbounded
        if not self.settings.investment.use_unbounded_capacity_addition_carbon:
            return attr
        iogp_projects = IOGPCarbonStorageProjects(
            settings=self.settings, source_path=self.source_path
        )
        data = iogp_projects.get_capacity_existing_data()
        median_add = data.median()
        return attr.set_data(
            default_value=median_add,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The unbounded capacity addition of carbon storage is based on the "
                    "median existing and future capacity from the IOGP report, divided "
                    "by the number of nodes in the dataset."
                ),
                metadata=iogp_projects.metadata,
            ),
        )
