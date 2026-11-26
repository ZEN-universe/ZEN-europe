from zen_creator import Sector

from zen_europe.elements.carriers.passenger_mileage import PassengerMileage
from zen_europe.elements.conversion_technologies.BEV import BEV
from zen_europe.elements.conversion_technologies.ICE_diesel import ICE_diesel
from zen_europe.elements.conversion_technologies.ICE_petrol import ICE_petrol


class PassengerTransportSector(Sector):
    """Passenger vehicle transport demand."""

    name = "passenger_transport"
    required_sectors = ["electricity", "oil_products"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            BEV,
            ICE_diesel,
            ICE_petrol,
            PassengerMileage,
        ]
