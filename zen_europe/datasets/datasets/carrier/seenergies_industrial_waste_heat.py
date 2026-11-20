from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class SeenergiesIndustrialWasteHeat(Dataset[dict[str, pd.DataFrame]]):
    """
    sEEnergies industrial waste heat dataset class.

    This class implements the specific behavior for the 
    sEEnergies industrial waste heat dataset.
    """

    name = "seenergies_industrial_waste_heat"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "sEEnergies - Excess heat potentials of industrial sites in Europe D5.1"
            ),
            author=["Tobias Fleiter",
                    "Pia Manz",
                    "Marius Neuwirth",
                    "Felix Mildner",
                    "Urban Persson",
                    "Katerina Kermeli",
                    "Wina Crijns-Graus",
                    "Cathelijne Rutten",],
            publication="Horizon 2020 - sEEnergies",
            publication_year=2020,
            url="https://www.seenergies.eu/wp-content/uploads/sites/25/2020/04/sEEnergies-WP5_D5.1-Excess_heat_potentials_of_industrial_sites_in_Europe.pdf",
            note="Project link: https://www.seenergies.eu/",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        return pd.Series({})

    # -------- methods ------------------------
    def get_waste_heat_share_glass(self) -> float:
        """
        Get the share of waste heat from glass production per fuel input.
        Assume that the recoverable waste heat is available at 55°C (level 2).
        Regenerative furnace, difference between no batch/cullet preheating and
            batch/cullet preheating (Table 7).

        """
        return 0.18 - 0.07

    def get_waste_heat_share_cement(self) -> float:
        """
        Get the share of waste heat from cement production per cement fuel input.
        Assume that the recoverable waste heat is available at 55°C (level 2).
        Dry kiln with preheater (Table 8), whose fuel use of 3.7 GJ/t clinker
        matches the cement kiln of the model; assume that all waste heat is
        recoverable.

        """
        return 0.17

    def get_waste_heat_steel(self) -> dict[str, float]:
        """
        Get the waste heat from steel production in GJ per tonne of steel.
        Assume that the recoverable waste heat is available at 55°C (level 2).
        The shares in Table 11 refer to the fuel of the individual unit (Fuel SEC),
        not to the total input of the route, so they are multiplied by it.
        BF-BOF: blast stove exhaust, difference between no heat recovery
            (10% of 1.5 GJ/t) and heat recovery with heat exchanger (4% of 1.4 GJ/t),
            plus the sensible heat of the BOF off-gases, difference between no heat
            recovery (0.55 GJ/t) and heat recovery (0.02 GJ/t). The coke ovens are
            not included.
        NG-DRI: electric arc furnace, as EAF (no data given for the DRI process)
        H2-DRI: electric arc furnace, as EAF (no data given for the DRI process)
        EAF: electric arc furnace, difference between no heat recovery
            (12% of 1.8 GJ/t) and scrap preheating (1% of 1.5 GJ/t).

        """
        eaf = 0.12 * 1.8 - 0.01 * 1.5
        return {
            "BF_BOF": 0.10 * 1.5 - 0.04 * 1.4 + 0.55 - 0.02,
            "NG_DRI": eaf,
            "H2_DRI": eaf,
            "EAF": eaf,
        }

    def get_waste_heat_paper(self) -> float:
        """
        Get the share of waste heat from paper production per input carrier.
        Assume that the recoverable waste heat is available at 55°C (level 2).
        Paper making, board&packaging paper, difference between no boiler heat recovery
            and boiler heat recovery.
        """
        return 0.03-0.02

    