from typing import ClassVar

from pydantic import Field
from zen_creator.utils.settings import SettingsCategory


class StructureSettings(SettingsCategory):
    """Selection of the energy system, sectors, technologies and carriers."""

    name: ClassVar[str] = "structure"
    controls: ClassVar[dict[str, str]] = {
        "energy_system": "elements.insert.energy_system",
        "set_sectors": "elements.insert.set_sectors",
        "set_conversion_technologies": "elements.insert.set_conversion_technologies",
        "set_storage_technologies": "elements.insert.set_storage_technologies",
        "set_transport_technologies": "elements.insert.set_transport_technologies",
        "set_retrofitting_technologies": (
            "elements.insert.set_retrofitting_technologies"
        ),
        "set_carriers": "elements.insert.set_carriers",
        "remove_sectors": "elements.exclude_sectors",
        "remove_technologies": "elements.exclude_elements",
    }

    energy_system: str = "energy_system_nuts0"
    set_sectors: list[str] = Field(
        default_factory=lambda: [
            "electricity",
            "carbon",
            "gas",
            "heat",
            "district_heating",
            "hydrogen",
            "ammonia",
            "cement",
            "methanol",
            "refining",
            "aviation",
            "shipping",
            "steel",
            "passenger_transport",
            "truck_transport",
            "glass",
            "ceramic",
            "paper",
            "food",
        ]
    )
    set_conversion_technologies: list[str] = Field(default_factory=list)
    set_storage_technologies: list[str] = Field(default_factory=list)
    set_transport_technologies: list[str] = Field(default_factory=list)
    set_retrofitting_technologies: list[str] = Field(default_factory=list)
    set_carriers: list[str] = Field(default_factory=list)
    remove_sectors: list[str] = Field(default_factory=list)
    remove_technologies: list[str] = Field(default_factory=list)
