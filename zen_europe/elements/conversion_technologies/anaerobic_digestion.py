from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.financial.dea import DEA

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, ConversionTechnology, SourceInformation


class AnaerobicDigestion(ConversionTechnology):
    """Class containing all data and assumptions for anaerobic digestion
    (wet biomass to biomethane)."""

    name: str = "anaerobic_digestion"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of anaerobic digestion to biomethane.
        """
        return Attribute(
            name="reference_carrier", default_value=["biomethane"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of anaerobic digestion to wet biomass,
        electricity and heat.
        """
        return Attribute(
            name="input_carrier",
            default_value=["wet_biomass", "electricity", "heat"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of anaerobic digestion to biomethane.
        """
        return Attribute(
            name="output_carrier", default_value=["biomethane"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of anaerobic digestion.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of anaerobic digestion.

        """
        attr = self.conversion_factor
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_anaerobic_digestion()
        source = SourceInformation(
            description=(
                "The conversion factor of anaerobic digestion is obtained from the DEA "
                "dataset for renewable fuels"
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of anaerobic digestion.

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
        Sets the specific capital expenditure (capex) for anaerobic digestion.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for anaerobic
        digestion.

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
        anaerobic digestion.

        The technology cost database does not contain any variable opex data for
        anaerobic digestion, so this method returns the default value of the attribute.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        attr = self.opex_specific_variable
        return attr
