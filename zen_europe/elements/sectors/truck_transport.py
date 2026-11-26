from zen_creator import Sector

from zen_europe.elements.carriers.truck_mileage import TruckMileage
from zen_europe.elements.conversion_technologies.HDT_BET import HDT_BET
from zen_europe.elements.conversion_technologies.HDT_diesel import HDT_diesel
from zen_europe.elements.conversion_technologies.HDT_FCEV import HDT_FCEV


class TruckTransportSector(Sector):
    """Truck freight transport demand."""

    name = "truck_transport"
    required_sectors = ["electricity", "oil_products"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            HDT_BET,
            HDT_diesel,
            HDT_FCEV,
            TruckMileage,
        ]
