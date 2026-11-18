from zen_creator import Sector

from zen_europe.elements.carriers.ammonia import Ammonia
from zen_europe.elements.conversion_technologies.ammonia_ICE_ship import (
    AmmoniaICEShip,
)
from zen_europe.elements.conversion_technologies.haber_bosch import HaberBosch
from zen_europe.elements.storage_technologies.industry_DSM import AmmoniaDSM
from zen_europe.elements.transport_technologies.ammonia_pipeline import (
    AmmoniaPipeline,
)


class AmmoniaSector(Sector):
    """Ammonia production and transport."""

    name = "ammonia"
    required_sectors = ["electricity", "hydrogen"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            HaberBosch,
            AmmoniaPipeline,
            AmmoniaICEShip,
            Ammonia,
            AmmoniaDSM,
        ]
