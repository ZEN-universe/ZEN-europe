from zen_creator import Sector

from zen_europe.elements.carriers.crude_oil import CrudeOil
from zen_europe.elements.carriers.naphtha import Naphtha
from zen_europe.elements.conversion_technologies.diesel_ICE_ship import DieselICEShip
from zen_europe.elements.conversion_technologies.oil_to_diesel_conversion import (
    OilToDieselConversion,
)
from zen_europe.elements.conversion_technologies.oil_to_gasoline_conversion import (
    OilToGasolineConversion,
)
from zen_europe.elements.conversion_technologies.oil_to_kerosene_conversion import (
    OilToKeroseneConversion,
)
from zen_europe.elements.conversion_technologies.oil_to_naphtha_conversion import (
    OilToNaphthaConversion,
)
from zen_europe.elements.conversion_technologies.olefin_from_naphtha import (
    OlefinFromNaphtha,
)
from zen_europe.elements.conversion_technologies.refining import Refining
from zen_europe.elements.storage_technologies.oil_storage import OilStorage
from zen_europe.elements.transport_technologies.oil_pipeline import OilPipeline


class RefiningSector(Sector):
    """Crude oil refining into gasoline, diesel, naphtha and kerosene."""

    name = "refining"
    required_sectors = ["hydrogen"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            OilToGasolineConversion,
            OilToDieselConversion,
            OilToNaphthaConversion,
            OilPipeline,
            OilStorage,
            Refining,
            OlefinFromNaphtha,
            OilToKeroseneConversion,
            DieselICEShip,
            CrudeOil,
            Naphtha,
        ]
