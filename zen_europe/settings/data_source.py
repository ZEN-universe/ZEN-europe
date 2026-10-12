from typing import ClassVar, Literal

from zen_creator.utils.settings import SettingsCategory


class DataSourceSettings(SettingsCategory):
    """Settings controlling which data sources are used."""

    name: ClassVar[str] = "data_source"

    use_full_scigrid_dataset: bool = False
    use_OG_carbon_storage_limit: bool = True
    use_monthly_entsoe_ntc: bool = True
    potential_capacity_power_line: Literal["candidates", "tyndp", "both"] = "candidates"
    use_plant_level_hydro_capacity: bool = False
