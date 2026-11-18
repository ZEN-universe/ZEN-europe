# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_creator.model import Model


class HeatIndustry:
    """Process heat or kiln fuel of one industry heat sector."""

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_export_yearly(self) -> Attribute:
        """Unlimited yearly export."""
        return self.availability_export_yearly.set_data(
            default_value=np.inf,
            unit="GWh",
            source=AssumptionInformation(description="No export limit."),
        )


class HeatIndustry0100Glass(HeatIndustry, Carrier):
    name: str = "heat_industry_0_100_glass"


class HeatIndustry0100Ceramic(HeatIndustry, Carrier):
    name: str = "heat_industry_0_100_ceramic"


class HeatIndustry0100Paper(HeatIndustry, Carrier):
    name: str = "heat_industry_0_100_paper"


class HeatIndustry0100Food(HeatIndustry, Carrier):
    name: str = "heat_industry_0_100_food"


class HeatIndustry100150Glass(HeatIndustry, Carrier):
    name: str = "heat_industry_100_150_glass"


class HeatIndustry100150Ceramic(HeatIndustry, Carrier):
    name: str = "heat_industry_100_150_ceramic"


class HeatIndustry100150Paper(HeatIndustry, Carrier):
    name: str = "heat_industry_100_150_paper"


class HeatIndustry100150Food(HeatIndustry, Carrier):
    name: str = "heat_industry_100_150_food"


class HeatIndustry150200Glass(HeatIndustry, Carrier):
    name: str = "heat_industry_150_200_glass"


class HeatIndustry150200Ceramic(HeatIndustry, Carrier):
    name: str = "heat_industry_150_200_ceramic"


class HeatIndustry150200Paper(HeatIndustry, Carrier):
    name: str = "heat_industry_150_200_paper"


class HeatIndustry150200Food(HeatIndustry, Carrier):
    name: str = "heat_industry_150_200_food"
