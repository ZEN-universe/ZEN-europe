from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Element


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.entsog import (
    ENTSOG,
    ENTSOGTransmissionCapacityMap,
)
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.carrier.import_increase_gas import ImportIncreaseGas
from zen_europe.datasets.datasets.technology.scigrid import SciGridIGGIELGNC1
from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import interpolate_missing_years, link_natural_gas_countries


class NaturalGasAvailability(DatasetCollection):
    """Extracting natural gas availability data."""

    name = "natural_gas_availability"

    def __init__(self, source_path: Path | str, settings: Settings):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "scigrid": SciGridIGGIELGNC1(self.source_path),
            "entsogTCM": ENTSOGTransmissionCapacityMap(self.source_path),
            "entsog": ENTSOG(self.source_path),
            "import_increase_gas": ImportIncreaseGas(self.source_path),
            "eurostat": Eurostat(source_path=self.source_path, settings=self.settings),
        }

    def get_availability_import(self, element: Element) -> Attribute:
        """
        Get the import availability for natural gas.

        This function retrieves the natural gas import availability data for the
        specified element.
        """
        scigrid_dataset = cast(SciGridIGGIELGNC1, self.data["scigrid"])
        entsogTCM = cast(ENTSOGTransmissionCapacityMap, self.data["entsogTCM"])
        entsog = cast(ENTSOG, self.data["entsog"])
        entsog_data = entsog.get_availability_natural_gas()
        import_gas, import_gas_RU = scigrid_dataset.get_pipeline_availability(
            element=element
        )
        import_gas, import_gas_RU = entsogTCM.adjust_by_additional_gas_import(
            import_gas=import_gas, import_gas_RU=import_gas_RU
        )
        import_gas = import_gas.rename(
            {"import": "availability_import", "export": "availability_export"}, axis=1
        )
        import_gas = import_gas["availability_import"]

        # adjust by ENTSOG potentials
        entsog_gas_availability = entsog_data / 365 / 24
        entsog_gas_availability = entsog_gas_availability.droplevel(0, axis=1)
        entsog_gas_availability.columns = entsog_gas_availability.columns.astype(int)
        linked_areas = link_natural_gas_countries()
        optimization_years = element.settings.time.years
        availability_yearly_variation = pd.DataFrame(
            index=import_gas.index, columns=optimization_years
        )
        for linked_area in linked_areas:
            availability_linked_country = entsog_gas_availability.loc[linked_area, :]
            if isinstance(availability_linked_country, pd.DataFrame):
                availability_linked_country = availability_linked_country.sum(axis=0)
            linked_countries = linked_areas[linked_area]
            import_gas_linked = import_gas[linked_countries].sum()
            availability_linked_country = interpolate_missing_years(
                availability_linked_country
            ).clip(upper=import_gas_linked)
            availability_linked_country = availability_linked_country.reindex(
                optimization_years, method="ffill"
            )
            import_gas[linked_countries] *= (
                availability_linked_country[element.settings.time.reference_year]
                / import_gas_linked
            )
            availability_yearly_variation.loc[linked_countries, :] = (
                availability_linked_country
                / availability_linked_country[element.settings.time.reference_year]
            ).values
            if linked_area == "Russia":
                import_gas_RU *= (
                    availability_linked_country[element.settings.time.reference_year]
                    / import_gas_linked
                )
        # add norway gas availability
        availability_norway_years = interpolate_missing_years(
            entsog_gas_availability.loc["Norway", :]
        )
        availability_norway = pd.Series(
            availability_norway_years[element.settings.time.reference_year],
            index=["NO"],
        )
        import_gas = pd.concat([import_gas, availability_norway]).sort_index()
        import_gas.name = "availability_import"
        import_gas.index.name = "node"
        availability_norway_yearly_variation = (
            availability_norway_years
            / availability_norway_years[element.settings.time.reference_year]
        )
        availability_norway_yearly_variation = (
            availability_norway_yearly_variation.reindex(
                optimization_years, method="ffill"
            )
        )
        availability_norway_yearly_variation.name = "NO"
        availability_yearly_variation = pd.concat(
            [
                availability_yearly_variation,
                availability_norway_yearly_variation.to_frame().T,
            ],
            axis=0,
        ).sort_index()
        availability_yearly_variation = availability_yearly_variation.stack()
        availability_yearly_variation.name = "availability_import"
        availability_yearly_variation.index.names = ["node", "year"]
        # add domestic production from Eurostat
        eurostat_dataset = cast(Eurostat, self.data["eurostat"])
        domestic_production = (
            eurostat_dataset.get_natural_gas_production() / Constants.HOURS_PER_YEAR
        )
        missing_countries = pd.Index(element.model.config.system.set_nodes).difference(
            domestic_production.index
        )
        # exclude Norway from domestic production, because already included in
        # import_gas
        common_countries = (
            pd.Index(element.model.config.system.set_nodes)
            .difference(["NO"])
            .intersection(domestic_production.index)
        )
        domestic_production = domestic_production.loc[common_countries]
        for country in missing_countries:
            if country != "CH":
                raise ValueError(
                    f"Missing domestic production data for country: " f"{country}"
                )
        import_gas = import_gas.add(domestic_production.squeeze(), fill_value=0)
        import_gas = import_gas[import_gas != 0]

        # reduce import_gas for countries tied to Russia
        import_gas = import_gas.subtract(import_gas_RU, fill_value=0)

        import_gas.name = "availability_import"
        import_gas.index.name = "node"

        source = SourceInformation(
            description=(
                "Natural gas import availability data is derived from multiple "
                "sources. First, the SciGRID dataset is used to calculate the import "
                "availability of natural gas through cross-border pipelines. Second, "
                "the ENTSOG Transmission Capacity Map (TCM) dataset is used to adjust "
                "the import availability by adding additional gas import capacity that "
                "is not yet part of the SciGRID Database. Third, the ENTSOG dataset is "
                "used to adjust the import availability by considering the increase in "
                "natural gas imports from other countries. Finally, the Eurostat "
                "dataset is used to add domestic production of natural gas."
            ),
            metadata=self.metadata,
        )
        return element.availability_import.set_data(
            source=source,
            df=import_gas,
            yearly_variations_df=availability_yearly_variation,
            unit="GW",
        )
