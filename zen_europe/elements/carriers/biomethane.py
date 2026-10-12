from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import Carrier


class Biomethane(Carrier):
    """Biomethane carrier class.

    This class implements the specific behavior for the biomethane carrier.
    """

    name: str = "biomethane"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------
