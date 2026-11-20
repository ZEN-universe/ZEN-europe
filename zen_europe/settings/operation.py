from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class OperationSettings(SettingsCategory):
    """Max-load settings."""

    name: ClassVar[str] = "operation"
    
    use_seasonal_nuclear_max_load: bool = True
    use_nodal_nuclear_max_load: bool = True
    use_industrial_waste_heat: bool = True
