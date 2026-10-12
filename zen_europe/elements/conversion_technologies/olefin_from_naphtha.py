from __future__ import annotations

from typing import TYPE_CHECKING, cast

from zen_europe.datasets.dataset_collections.olefin_demand import OlefinDemand
from zen_europe.datasets.datasets.carrier.aidres import Aidres

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class OlefinFromNaphtha(ConversionTechnology):
    """Class containing all data and assumptions for olefin production
    from naphtha."""

    name: str = "olefin_from_naphtha"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of olefin from naphtha to olefin.
        """
        return Attribute(
            name="reference_carrier", default_value=["olefin"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of olefin from naphtha to naphtha and
        electricity.
        """
        return Attribute(
            name="input_carrier", default_value=["naphtha", "electricity"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of olefin from naphtha to olefin.
        """
        return Attribute(name="output_carrier", default_value=["olefin"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of olefin from naphtha.

        """
        attr = self.lifetime
        m_ng = self.model.conversion_technologies["methanol_from_natural_gas"]
        lifetime_methanol = m_ng.lifetime.default_value
        attr.set_data(
            default_value=lifetime_methanol,
            source=SourceInformation(
                description=(
                    "The lifetime of olefin from naphtha is manually set "
                    "to the lifetime of methanol from natural gas, "
                    "assuming a standard industrial technology lifetime."
                ),
                metadata=cast(SourceInformation, m_ng.lifetime.sources[-1]).metadata,
            ),
        )
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of olefin from naphtha.

        """
        if self.settings.investment.use_construction_times:
            attr = self.construction_time
            m_ng = self.model.conversion_technologies["methanol_from_natural_gas"]
            construction_time_methanol = m_ng.construction_time.default_value
            attr.set_data(
                default_value=construction_time_methanol,
                source=SourceInformation(
                    description=(
                        "The construction time of olefin from naphtha is "
                        "manually set to the construction time of methanol "
                        "from natural gas, assuming a standard "
                        "industrial construction timeline."
                    ),
                    metadata=cast(
                        SourceInformation, m_ng.construction_time.sources[-1]
                    ).metadata,
                ),
            )
            return attr
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of olefin from naphtha.

        """
        attr = self.conversion_factor
        aidres_dataset = Aidres(source_path=self.source_path)
        cf_dict = aidres_dataset.get_conversion_factors_aidres(self.name)
        cf = [
            {
                carrier: {"default_value": value, "unit": "GWh/tproduct"}
                for carrier, value in cf_dict.items()
            }
        ]
        source = SourceInformation(
            description=(
                "The conversion factor of olefin from naphtha is obtained "
                "from the Aidres dataset (Table 32, NTO-to-olefin route)."
            ),
            metadata=aidres_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) of olefin from naphtha.

        """
        aidres_dataset = Aidres(source_path=self.source_path)
        return aidres_dataset.get_capex_specific_olefin(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of olefin from naphtha.

        """
        if self.settings.investment.use_existing_capacities:
            olefin_dataset = OlefinDemand(
                source_path=self.source_path, settings=self.settings
            )
            return olefin_dataset.get_capacity_existing_olefin(self)
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
