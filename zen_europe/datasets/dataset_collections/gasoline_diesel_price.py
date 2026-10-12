from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Carrier, Dataset


from zen_creator import Attribute, DatasetCollection
from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.carrier.bnef_fuelprices import BNEFFuelPrices
from zen_europe.datasets.datasets.carrier.gasoline_diesel_spread import (
    GasolineDieselSpread,
)


class GasolineDieselPrice(DatasetCollection):
    """Extracting gasoline and diesel price data."""

    name = "gasoline_diesel_price"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "bnef": BNEFFuelPrices(self.source_path),
            "gasoline_diesel_spread": GasolineDieselSpread(self.source_path),
        }

    def get_price_import(self, element: Carrier) -> Attribute:
        """
        Get the import price for gasoline and diesel.

        This function retrieves the gasoline and diesel price data for the specified
        element.
        """
        bnef_dataset = cast(BNEFFuelPrices, self.data["bnef"])
        data = bnef_dataset.get_price_import_data(element, manual_carrier_name="oil")
        gasoline_diesel_spread_dataset = cast(
            GasolineDieselSpread, self.data["gasoline_diesel_spread"]
        )
        spread = gasoline_diesel_spread_dataset.get_crack_spread()

        data = data * (1 + spread)
        default_value = data.loc[element.settings.time.reference_year]
        yearly_variations_df = data / default_value
        yearly_variations_df.index.name = "year"
        yearly_variations_df.name = "price_import_yearly_variation"

        source = SourceInformation(
            description=(
                "The gasoline and diesel price data is assumed to follow the oil price"
                " from the BNEF dataset, "
                "and the crack spread is assumed to be stationary."
            ),
            metadata=self.metadata,
        )
        return element.price_import.set_data(
            source=source,
            default_value=default_value,
            yearly_variations_df=yearly_variations_df,
            unit="Euro/MWh",
        )

    def get_opex_specific_variable_oil_conversion(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Get the specific variable opex from the gasoline diesel spread.

        Applies to the oil_to_gasoline and oil_to_diesel conversion technologies.
        """
        bnef_dataset = cast(BNEFFuelPrices, self.data["bnef"])
        data = bnef_dataset.get_price_import_data(element, manual_carrier_name="oil")
        default_value = data.loc[element.settings.time.reference_year]
        spread_dataset = cast(GasolineDieselSpread, self.data["gasoline_diesel_spread"])
        spread_rel = spread_dataset.get_crack_spread()
        spread = default_value * spread_rel
        yearly_variations_df = (data * spread_rel) / default_value
        yearly_variations_df.index.name = "year"
        yearly_variations_df.name = "opex_specific_variable_yearly_variation"
        attr = element.opex_specific_variable
        return attr.set_data(
            default_value=spread,
            unit="Euro/MWh",
            yearly_variations_df=yearly_variations_df,
            source=SourceInformation(
                description=(
                    "We assume a constant relative spread between the price for"
                    " diesel and gasoline, and oil. This is added as a specific"
                    " variable opex to the conversion technology"
                ),
                metadata=self.metadata,
            ),
        )
