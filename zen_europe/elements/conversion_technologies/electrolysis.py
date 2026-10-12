from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pandas as pd

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.hydrogen_europe import HydrogenEurope
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)
from zen_europe.utils.utils import format_capacity_existing

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class Electrolysis(ConversionTechnology):
    """Class containing all data and assumptions for electrolysis."""

    name: str = "electrolysis"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of electrolysis to hydrogen.
        """
        return Attribute(
            name="reference_carrier", default_value=["hydrogen"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of electrolysis to natural gas.
        """
        return Attribute(
            name="input_carrier", default_value=["electricity"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of electrolysis to hydrogen.
        """
        return Attribute(
            name="output_carrier", default_value=["hydrogen"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of electrolysis.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of electrolysis.

        """
        attr = self.conversion_factor
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_electrolysis()
        source = SourceInformation(
            description=(
                "The conversion factor of electrolysis is obtained from the DEA "
                "dataset for renewable fuels"
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of electrolysis.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _electricity_conversion_factor(self) -> float:
        """Return the electricity input per unit of hydrogen output."""
        cf = cast(
            list[dict[str, dict[str, float]]], self.conversion_factor.default_value
        )
        return cf[0]["electricity"]["default_value"]

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for electrolysis.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        cf = self._electricity_conversion_factor()
        attr = tech_db.get_capex_specific_conversion(self)
        if attr.df is not None:
            data = cast(pd.Series, attr.df) * cf
            attr.set_data(df=data, source=attr.sources[-1])
        else:
            value = cast(float, attr.default_value) * cf
            attr.set_data(default_value=value, source=attr.sources[-1])
        return attr

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for electrolysis.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        cf = self._electricity_conversion_factor()
        attr = tech_db.get_opex_specific_fixed(self)
        if attr.df is not None:
            data = cast(pd.Series, attr.df) * cf
            attr.set_data(df=data, source=attr.sources[-1])
        else:
            value = cast(float, attr.default_value) * cf
            attr.set_data(default_value=value, source=attr.sources[-1])
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for electrolysis.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        cf = self._electricity_conversion_factor()
        attr = tech_db.get_opex_specific_variable(self)
        if attr.df is not None:
            data = cast(pd.Series, attr.df) * cf
            attr.set_data(df=data, source=attr.sources[-1])
        else:
            value = cast(float, attr.default_value) * cf
            attr.set_data(default_value=value, source=attr.sources[-1])
        return attr

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for electrolysis.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            hydrogen_europe_dataset = HydrogenEurope(source_path=self.source_path)
            raw_capacity = hydrogen_europe_dataset.get_capacity_existing()
            cf = self._electricity_conversion_factor()
            capacity_existing = format_capacity_existing(
                cast(pd.Series, raw_capacity.squeeze()) / cf
            )
            attr = self.capacity_existing
            source = SourceInformation(
                description=(
                    "The existing capacity of electrolysis is based on data from "
                    "Hydrogen Europe (2024). The data is reported in electricity "
                    "units, so we convert it to H2 quantities."
                ),
                metadata=hydrogen_europe_dataset.metadata,
            )
            attr.set_data(df=capacity_existing, source=source, unit="MW")
            return attr
        else:
            attr = self.capacity_existing
            attr.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description=("We do not consider existing capacities."),
                ),
            )
            return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of electrolysis.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
