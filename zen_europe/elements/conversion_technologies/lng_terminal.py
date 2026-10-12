from __future__ import annotations

from typing import TYPE_CHECKING, cast

from zen_europe.datasets.datasets.technology.gie_lng_map import GIELNGMap
from zen_europe.datasets.datasets.technology.lng_regasification_toledano import (
    LNGRegasificationToledano,
)
from zen_europe.datasets.datasets.technology.lng_terminals_brauers import (
    LNGTerminalsBrauers,
)
from zen_europe.datasets.datasets.technology.lng_terminals_zeal import LNGTerminalsZeal
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np
import pandas as pd
from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class LNGTerminal(ConversionTechnology):
    """Class containing all data and assumptions for LNG terminals (regasification)."""

    name: str = "lng_terminal"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of LNG terminals to natural gas.
        """
        return Attribute(
            name="reference_carrier", default_value=["natural_gas"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of LNG terminals to LNG.
        """
        return Attribute(name="input_carrier", default_value=["lng"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of LNG terminals to natural gas.
        """
        return Attribute(
            name="output_carrier", default_value=["natural_gas"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of LNG terminals.

        """
        lng_terminals = LNGTerminalsBrauers(source_path=self.source_path)
        return lng_terminals.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of LNG terminals.

        """
        if self.settings.investment.use_construction_times:
            lng_terminals = LNGTerminalsZeal(source_path=self.source_path)
            return lng_terminals.get_construction_time(self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of LNG terminals.

        Regasification is assumed to be lossless (1 unit of LNG produces 1 unit
        of natural gas).
        """
        attr = self.conversion_factor
        cf = [{"lng": {"default_value": 1, "unit": "GWh/GWh"}}]
        attr.set_data(
            default_value=cf,
            source=AssumptionInformation(
                description=(
                    "The conversion factor of LNG terminals is manually set to 1, "
                    "assuming lossless regasification of LNG to natural gas."
                ),
            ),
        )
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for LNG terminals.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        regasification = LNGRegasificationToledano(source_path=self.source_path)
        return regasification.get_opex_specific_variable(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for LNG terminals.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        lng_terminals = LNGTerminalsBrauers(source_path=self.source_path)
        return lng_terminals.get_capex_specific(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for LNG terminals.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            gie_lng_map = GIELNGMap(source_path=self.source_path)
            capacity_existing = gie_lng_map._calculate_capacity_existing_lng(self)
            attr = self.capacity_existing
            source = SourceInformation(
                description=(
                    "The existing capacity of LNG terminals is derived from the "
                    "SciGRID GIE dataset of LNG terminal storage-to-pipeline "
                    "send-out capacities."
                ),
                metadata=gie_lng_map.metadata,
            )
            attr.set_data(df=capacity_existing, source=source, unit="GW")
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

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit for LNG terminals.

        The capacity limit is computed as the existing capacity multiplied by
        the TYNDP 2022 LNG potential-increase factor.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        attr = self.capacity_limit
        data = cast(pd.Series, self.capacity_existing.df)
        if data is None:
            gie_lng_map = GIELNGMap(source_path=self.source_path)
            data = gie_lng_map._calculate_capacity_existing_lng(self)
        capacity_limit = data.groupby(level=0).sum()
        capacity_limit.loc[:] = np.inf
        capacity_limit.name = "capacity_limit"
        attr.set_data(
            df=capacity_limit,
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "Assume infinite capacity limit for those countries "
                    "with existing lng terminals."
                ),
            ),
            unit="GW",
        )
        return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of lng terminal.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)
