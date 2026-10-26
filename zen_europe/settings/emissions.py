from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class EmissionsSettings(SettingsCategory):
    """Emissions and carbon-budget settings."""

    name: ClassVar[str] = "emissions"

    use_carbon_budget: bool = True
    use_carbon_annual_limit: bool = False
    use_annual_limit_overshoot: bool = True
    use_EU_ETS_cap: bool = False
    temperature_increase: float = 1.5
    probability_carbon_budget: float = 0.5
    extrapolate_missing_years: bool = True
