from zen_creator import Sector

from zen_europe.elements.carriers.methanol import Methanol
from zen_europe.elements.carriers.olefin import Olefin
from zen_europe.elements.conversion_technologies.methanol_from_biomass import (
    MethanolFromBiomass,
)
from zen_europe.elements.conversion_technologies.methanol_from_hydrogen import (
    MethanolFromHydrogen,
)
from zen_europe.elements.conversion_technologies.methanol_from_natural_gas import (
    MethanolFromNaturalGas,
)
from zen_europe.elements.conversion_technologies.methanol_ICE_ship import (
    MethanolICEShip,
)
from zen_europe.elements.conversion_technologies.olefin_from_methanol import (
    OlefinFromMethanol,
)
from zen_europe.elements.conversion_technologies.olefin_from_naphtha import (
    OlefinFromNaphtha,
)
from zen_europe.elements.storage_technologies.industry_DSM import (
    MethanolDSM,
    OlefinDSM,
)
from zen_europe.elements.transport_technologies.methanol_pipeline import (
    MethanolPipeline,
)
from zen_europe.elements.transport_technologies.olefin_pipeline import OlefinPipeline


class MethanolSector(Sector):
    """Methanol and olefin production and transport."""

    name = "methanol"
    required_sectors = [
        "electricity",
        "district_heating",
        "hydrogen",
        "refining",
        "gas",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            MethanolFromNaturalGas,
            MethanolFromBiomass,
            OlefinFromMethanol,
            MethanolPipeline,
            OlefinPipeline,
            MethanolFromHydrogen,
            OlefinFromNaphtha,
            MethanolICEShip,
            Methanol,
            Olefin,
            MethanolDSM,
            OlefinDSM,
        ]
