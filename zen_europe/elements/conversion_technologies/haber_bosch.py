from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.ifa import IFA
from zen_europe.datasets.datasets.financial.dea import DEA

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, ConversionTechnology, SourceInformation


class HaberBosch(ConversionTechnology):
    """Class containing all data and assumptions for the Haber-Bosch process
    (hydrogen to ammonia)."""

    name: str = "haber_bosch"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of the Haber-Bosch process to ammonia.
        """
        return Attribute(
            name="reference_carrier", default_value=["ammonia"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of the Haber-Bosch process to hydrogen and
        electricity.
        """
        return Attribute(
            name="input_carrier",
            default_value=["hydrogen", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of the Haber-Bosch process to ammonia.
        """
        return Attribute(name="output_carrier", default_value=["ammonia"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of the Haber-Bosch process.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of the Haber-Bosch process.

        """
        attr = self.conversion_factor
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_haber_bosch()
        source = SourceInformation(
            description=(
                "The conversion factor of the Haber-Bosch process is a "
                "manually derived value based on the DEA technology "
                "catalogue for renewable fuels (Green Ammonia plant: "
                "Hydrogen to ammonia, excl. electrolyzer and excl. air-"
                "separation unit)."
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of the Haber-Bosch process.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for the Haber-Bosch
        process.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for the
        Haber-Bosch process.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for the
        Haber-Bosch process.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of the Haber-Bosch process.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            ifa_dataset = IFA(source_path=self.source_path)
            return ifa_dataset.get_capacity_existing(self)
        else:
            return self.capacity_existing
