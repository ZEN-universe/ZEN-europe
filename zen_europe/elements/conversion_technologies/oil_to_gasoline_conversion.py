from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.existing_vehicle_capacity import (
    ExistingVehicleCapacity,
)
from zen_europe.datasets.dataset_collections.gasoline_diesel_price import (
    GasolineDieselPrice,
)


class OilToGasolineConversion(ConversionTechnology):
    """Class containing all data and assumptions for oil-to-gasoline
    conversion (a refinery output-shifting technology)."""

    name: str = "oil_to_gasoline_conversion"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)
        # set the inflation rate function from the ECB dataset
        # TODO make the inflation rate function directly available in the model,
        # so that it can be used by other elements as well
        ecb = ECBInflation(source_path=self.source_path)
        self.get_inflation_rate = ecb.get_inflation_rate
        ecb_dollar2euro = ECBDollar2Euro(source_path=self.source_path)
        self.get_dollar2euro = ecb_dollar2euro.get_dollar2euro

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of oil to gasoline conversion to gasoline.
        """
        return Attribute(
            name="reference_carrier", default_value=["gasoline"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of oil to gasoline conversion to oil.
        """
        return Attribute(name="input_carrier", default_value=["oil"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of oil to gasoline conversion to gasoline.
        """
        return Attribute(
            name="output_carrier", default_value=["gasoline"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of oil to gasoline conversion.

        """
        attr = self.lifetime
        attr.set_data(
            default_value=100,
            source=AssumptionInformation(
                description=(
                    "The lifetime of oil to gasoline conversion is "
                    "manually set to 100 years, effectively representing "
                    "an always-available refinery output-shifting "
                    "pathway rather than a capital asset with a finite "
                    "technical lifetime."
                ),
            ),
        )
        return attr

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of oil to gasoline conversion.

        Assumed lossless (1 unit of oil converted to 1 unit of gasoline).
        """
        attr = self.conversion_factor
        cf = [{"oil": {"default_value": 1, "unit": "GWh/GWh"}}]
        attr.set_data(
            default_value=cf,
            source=AssumptionInformation(
                description=(
                    "The conversion factor of oil to gasoline conversion "
                    "is manually set to 1, assuming a lossless output shift "
                    "within the refinery product slate."
                ),
            ),
        )
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        """Return the specific variable opex of oil to gasoline conversion.

        The opex is the spread between oil and gasoline.
        """
        if not self.settings.cost.assume_oil_price_for_diesel_and_gasoline:
            gasoline_diesel_price = GasolineDieselPrice(self.source_path)
            return gasoline_diesel_price.get_opex_specific_variable_oil_conversion(self)
        else:
            return self.opex_specific_variable

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of oil to gasoline conversion.

        The refinery has to be able to supply the gasoline that the existing
        passenger cars burn.
        """
        if not (
            self.settings.investment.use_existing_capacities
            and self.settings.investment.use_existing_oil_to_x_capacities
        ):
            attr = self.capacity_existing
            attr.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description=(
                        "We do not consider existing capacities of the "
                        "refinery output-shifting technologies."
                    ),
                ),
            )
            return attr

        vehicle_capacity = ExistingVehicleCapacity(
            settings=self.model.settings, source_path=self.source_path
        )
        return vehicle_capacity.get_existing_capacity_oil_conversion(element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of oil to gasoline conversion.

        Without existing capacities the technology cannot grow from a zero
        base, so the diffusion rate is left unbounded.
        """
        if (
            not self.settings.investment.use_diffusion_rates
            or not self.settings.investment.use_existing_oil_to_x_capacities
        ):
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
