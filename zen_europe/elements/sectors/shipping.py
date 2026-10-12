from zen_creator import Sector

from zen_europe.elements.carriers.shipping import Shipping
from zen_europe.elements.conversion_technologies.ammonia_ICE_ship import (
    AmmoniaICEShip,
)
from zen_europe.elements.conversion_technologies.diesel_ICE_ship import DieselICEShip
from zen_europe.elements.conversion_technologies.hydrogen_FC_ship import (
    HydrogenFCShip,
)
from zen_europe.elements.conversion_technologies.methanol_ICE_ship import (
    MethanolICEShip,
)


class ShippingSector(Sector):
    """Shipping fuel demand, split by fuel technology."""

    name = "shipping"
    required_sectors = ["electricity", "hydrogen"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            DieselICEShip,
            HydrogenFCShip,
            MethanolICEShip,
            AmmoniaICEShip,
            Shipping,
        ]
