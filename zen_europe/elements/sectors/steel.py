from zen_creator import Sector

from zen_europe.elements.carriers.primary_steel import PrimarySteel
from zen_europe.elements.carriers.secondary_steel import SecondarySteel
from zen_europe.elements.conversion_technologies.BF_BOF import BF_BOF
from zen_europe.elements.conversion_technologies.EAF import EAF
from zen_europe.elements.conversion_technologies.H2_DRI import H2_DRI
from zen_europe.elements.conversion_technologies.NG_DRI import NG_DRI
from zen_europe.elements.conversion_technologies.pyrolysis import Pyrolysis
from zen_europe.elements.retrofitting_technologies.BF_BOF_CCS import BF_BOF_CCS
from zen_europe.elements.retrofitting_technologies.NG_DRI_CCS import NG_DRI_CCS
from zen_europe.elements.storage_technologies.industry_DSM import (
    PrimarySteelDSM,
    SecondarySteelDSM,
)


class SteelSector(Sector):
    """Primary and secondary steel production."""

    name = "steel"
    required_sectors = ["electricity", "gas"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            BF_BOF,
            NG_DRI,
            EAF,
            Pyrolysis,
            H2_DRI,
            BF_BOF_CCS,
            NG_DRI_CCS,
            PrimarySteel,
            SecondarySteel,
            PrimarySteelDSM,
            SecondarySteelDSM,
        ]
