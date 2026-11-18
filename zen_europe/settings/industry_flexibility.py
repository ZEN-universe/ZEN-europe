from typing import ClassVar, Literal

from pydantic import Field
from zen_creator.utils.settings import SettingsCategory


class IndustryFlexibilitySettings(SettingsCategory):
    """Flexibility and heat pump options of the industry sectors.

    Technologies that are switched off are removed from the model, see
    ``zen_europe.model_creator.remove_inactive_industry_elements``.
    """

    name: ClassVar[str] = "industry_flexibility"

    # thermal energy storage of the glass, ceramic, paper and food sectors
    use_tes: bool = True
    # DSM category column; "none" removes the DSM of all industrial products
    dsm_shiftability: Literal["optimistic", "pessimistic", "none"] = "optimistic"
    # temperature bands that have industry heat pumps; the other bands are supplied
    # via the temperature cascade
    heat_pump_temp_levels: list[Literal["0_100", "100_150", "150_200"]] = Field(
        default_factory=lambda: ["0_100", "100_150", "150_200"]
    )
