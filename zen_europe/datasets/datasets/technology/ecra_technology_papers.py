from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.attribute import Attribute

from zen_europe.utils.constants import Constants


class ECRATechnologyPapers(Dataset[pd.DataFrame]):
    """
    Dataset class for the state of the art cement manufacturing technology data from
    ECRA (European Cement Research Academy) technology papers.

    """

    name = "ecra_technology_papers"

    MONEY_YEAR = 2014

    # reference plant, Annex II, p. 185
    REFERENCE_CLINKER_CAPACITY = 2e6  # t clinker/a
    REFERENCE_FUEL_INTENSITY = 3.352  # GJ/t clinker

    # share of the kiln fuel demand that a fuel can cover at most
    SUBSTITUTION_POTENTIAL = {
        "coal_to_cement_fuel": 1.0,
        "waste_to_cement_fuel": 0.65,
        "biomass_to_cement_fuel": 0.4,
        "hydrogen_to_cement_fuel": 0.1,
    }

    # investment to reach the substitution potential at the reference plant, in Euro
    RETROFIT_INVESTMENT = {
        "waste_to_cement_fuel": 10e6,
        "biomass_to_cement_fuel": 15e6,
        "hydrogen_to_cement_fuel": 4.5e6,
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "THE ECRA TECHNOLOGY PAPERS 2022 - State of the Art Cement "
                "Manufacturing"
            ),
            author=["ECRA (European Cement Research Academy)"],
            publication="ECRA Technology Papers",
            publication_year=2022,
            url="https://www.ecra-online.org/research/technology-papers",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> dict[str, pd.Series]:
        """
        No data to be set.
        """
        data = {}

        data = pd.Series(data)
        return data

    # -------- methods ------------------------
    def get_substitution_potential(self, name: str) -> float:
        """
        Get the share of the kiln fuel demand that a cement fuel can cover at most.

        Hard coal is the reference fuel and is not limited. Waste is limited to the
        65% substitution rate of Technology Paper 14, biomass to the 30% share of
        Technology Paper 13, and hydrogen to the 10% share of the 2050 scenario of
        Technology Paper 18.

        Returns:
            float: The maximum share of the kiln fuel demand.
        """
        if name not in self.SUBSTITUTION_POTENTIAL:
            raise ValueError(f"Substitution potential for {name} is not defined.")
        return self.SUBSTITUTION_POTENTIAL[name]

    def get_capex_specific_retrofitting(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the specific capital expenditure (CAPEX) for the retrofitting
        of cement kilns to other feedstocks.

        The size and energy use values are taken from Annex II, p. 185.
        The substitution to biomass and waste is taken from Technology Paper 14,
        with the highest value (15 Mio Euro) used for the retrofitting to biomass
        because of the problems with high substitution rates of biomass.
        The retrofitting to waste is assumed to be lower (10 Mio Euro, average value).
        The substitution to hydrogen is taken from Technology paper 18,
        assuming the highest value of 4.5 Mio Euro for the retrofitting to hydrogen.
        Each investment only buys the substitution potential of the respective fuel,
        so it is divided by the share of the kiln fuel capacity it can cover.

        Returns:
            Attribute: An Attribute object containing the specific CAPEX data.
        """
        attr = element.capex_specific_conversion
        if element.name not in self.RETROFIT_INVESTMENT:
            raise ValueError(
                f"Specific CAPEX for retrofitting to {element.name} is not defined."
            )
        energy_use = self.REFERENCE_FUEL_INTENSITY / Constants.SECONDS_PER_HOUR  # GWh/t
        size = (
            self.REFERENCE_CLINKER_CAPACITY / Constants.HOURS_PER_YEAR * energy_use
        )  # t/a -> t/h -> GW
        capacity_retrofitted = size * self.get_substitution_potential(element.name)
        attr.set_data(
            default_value=self.RETROFIT_INVESTMENT[element.name] / capacity_retrofitted,
            source=SourceInformation(
                description=(
                    "The specific CAPEX for retrofitting cement kilns to other "
                    "feedstocks is derived from ECRA (2022), Technology Papers "
                    "2022.The size and energy use values are taken from Annex II, p. "
                    "185. The substitution to biomass and waste is taken from "
                    "Technology Paper 14,with the highest value (15 Mio Euro) used for "
                    "the retrofitting to biomassbecause of the problems with high "
                    "substitution rates of biomass. The retrofitting to waste is "
                    "assumed to be lower (10 Mio Euro, average value).The substitution "
                    "to hydrogen is taken from Technology paper 18, assuming the "
                    "highest value of 4.5 Mio Euro for the retrofitting to hydrogen. "
                    "Each investment only buys the substitution potential of the "
                    "respective fuel, so it is divided by the share of the kiln fuel "
                    "capacity it can cover."
                ),
                metadata=self.metadata,
            ),
            unit="Euro/GW",
        )
        return attr
