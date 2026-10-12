from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.rollout_hydrogen_ganter import (
    HydrogenRolloutGanter,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)

from zen_europe.utils.utils import (
    account_for_decommissioned_capacity,
    format_capacity_existing,
)


class SMR(ConversionTechnology):
    """Class containing all data and assumptions for Steam Methane Reforming (SMR).

    Note that this is not a small modular reactor, but a steam methane reformer for
    hydrogen production.
    """

    name: str = "SMR"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of SMR to hydrogen.
        """
        return Attribute(
            name="reference_carrier", default_value=["hydrogen"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of SMR to natural gas.
        """
        return Attribute(
            name="input_carrier", default_value=["natural_gas"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of SMR to hydrogen.
        """
        return Attribute(
            name="output_carrier",
            default_value=["hydrogen", "electricity"],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of SMR.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of SMR.

        """
        attr = self.conversion_factor
        ganter_dataset = HydrogenRolloutGanter(source_path=self.source_path)
        cf = ganter_dataset.get_conversion_factor_SMR()
        source = SourceInformation(
            description=(
                "The conversion factor of SMR is based on data from Ganter et al. "
                "(2024). "
            ),
            metadata=ganter_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of SMR.

        """
        if self.settings.investment.use_construction_times:
            # assume that the construction time of SMR is the same as for methanation,
            # as both are chemical conversion technologies
            methanation = self.model.conversion_technologies["methanation"]
            construction_time = methanation.construction_time.default_value
            attr = self.construction_time
            source = AssumptionInformation(
                description=(
                    "The construction time of SMR is assumed to be the same as for "
                    "methanation, as both are chemical conversion technologies."
                )
            )
            attr.set_data(default_value=construction_time, source=source)
            return attr
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for SMR.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for SMR.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for SMR.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for SMR.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            ganter_dataset = HydrogenRolloutGanter(source_path=self.source_path)
            capacity_existing = ganter_dataset.get_capacity_existing_SMR()
            capacity_existing = capacity_existing.to_frame(
                name=self.settings.time.reference_year - 1
            )
            capacity_existing = account_for_decommissioned_capacity(
                capacity_existing, self
            )
            capacity_existing.index.name = "node"
            capacity_existing = format_capacity_existing(capacity_existing)
            attr = self.capacity_existing
            source = SourceInformation(
                description=(
                    "The existing capacity of SMR is based on data from Ganter et al. "
                    "(2024). It is assumed that all current ammonia and refinery "
                    "plants are using SMR technology for hydrogen production."
                ),
                metadata=ganter_dataset.metadata,
            )
            attr.set_data(df=capacity_existing, source=source, unit="GW")
            return attr
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
        Sets the maximum diffusion rate of SMR.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
