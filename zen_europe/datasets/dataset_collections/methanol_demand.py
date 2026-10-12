from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    format_capacity_existing,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Element


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.carrier.manual_methanol_demand import (
    WITS,
    ChemAnalyst,
    Equinor,
)
from zen_europe.utils.constants import Constants


class MethanolDemand(DatasetCollection):
    """Extracting methanol demand data."""

    name = "methanol_demand"

    def __init__(self, source_path: Path | str):
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "aidres": Aidres(self.source_path),
            "wits": WITS(self.source_path),
            "equinor": Equinor(self.source_path),
            "chem_analyst": ChemAnalyst(self.source_path),
        }

    def _calculate_methanol_demand(self, element: Element) -> Attribute:
        """
        Calculate the methanol demand for the specified element.

        This function retrieves the methanol demand data for the specified element
        and returns it as an Attribute object.
        """
        aidres_dataset = cast(Aidres, self.data["aidres"])
        data = aidres_dataset.get_demand(element)
        wits_dataset = cast(WITS, self.data["wits"])
        equinor_dataset = cast(Equinor, self.data["equinor"])
        chem_analyst_dataset = cast(ChemAnalyst, self.data["chem_analyst"])

        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            data.index
        )

        data = data * 1000 / Constants.GJ_PER_MWH  # from PJ/year to GWh/year

        for country in missing_countries:
            if country == "CH":
                data.loc[country] = (
                    wits_dataset.get_manual_methanol_demand_wits(country)
                ) * aidres_dataset.get_energy_density_methanol()
            elif country == "UK":
                data.loc[country] = (
                    chem_analyst_dataset.get_manual_methanol_demand_chemanalyst(country)
                ) * aidres_dataset.get_energy_density_methanol()
            elif country == "NO":
                data.loc[country] = (
                    equinor_dataset.get_manual_methanol_demand_equinor(country)
                ) * aidres_dataset.get_energy_density_methanol()
            else:
                raise ValueError(
                    f"Methanol demand data for country {country} is not available in "
                    "the Aidres dataset or any of the manual datasets (WITS, Equinor, "
                    "ChemAnalyst). Please provide the necessary data for this country."
                )

        data = data.sort_index()

        data.index.name = "node"
        data.name = "demand"

        total_european_demand = (
            chem_analyst_dataset.get_total_european_demand()
            * aidres_dataset.get_energy_density_methanol()
            / Constants.HOURS_PER_YEAR
        )

        data = data / data.sum() * total_european_demand
        return data

    def get_methanol_demand(self, element: Element) -> Attribute:
        """
        Get the demand for methanol.

        This function retrieves the methanol demand data for the specified element.
        """
        data = self._calculate_methanol_demand(element)

        source = SourceInformation(
            description=(
                "Methanol demand data is derived from the Aidres dataset, which "
                "provides demand data for various industrial sectors. Additional "
                "manual data for missing countries is obtained from the following "
                "datasets:WITS, Equinor, and ChemAnalyst. The total European demand is "
                "derived from the ChemAnalyst dataset, because AIDRES assumes no "
                "current methanol demand.  Thus, we get the shares in 2030 from AIDRES "
                "and scale them to the total European demand in 2030 from ChemAnalyst."
            ),
            metadata=self.metadata,
        )
        return element.demand.set_data(
            source=source,
            df=data,
            unit="GW",
        )

    def get_capacity_existing(self, element: Element) -> Attribute:
        """
        Get the existing capacity for methanol from natural gas. We assume that all
        current methanol plants use natural gas as feedstock.

        This function retrieves the existing capacity data for the specified element.
        """
        methanol_element = element.model.carriers["methanol"]
        data = self._calculate_methanol_demand(methanol_element).squeeze()
        data = data.to_frame(name=element.settings.time.reference_year - 1) * 1000
        capacity_existing = calculate_capacity_addition_from_cumulative(data, element)
        capacity_existing = format_capacity_existing(capacity_existing)

        source = SourceInformation(
            description=(
                "The existing capacity for methanol from natural gas is derived from "
                "the methanol demand data. We assume that all current methanol plants "
                "use natural gas as feedstock. "
            ),
            metadata=self.metadata,
        )
        return element.capacity_existing.set_data(
            source=source, df=capacity_existing, unit="MW"
        )
