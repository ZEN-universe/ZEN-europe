from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class MaxLoadSettings(SettingsCategory):
    """Max-load settings."""

    name: ClassVar[str] = "max_load"

    use_seasonal_nuclear_max_load: bool = True
    use_nodal_nuclear_max_load: bool = True
