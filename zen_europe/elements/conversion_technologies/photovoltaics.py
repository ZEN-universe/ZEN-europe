from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import pandas as pd
from zen_creator import (
    Attribute,
    ConversionTechnology,
    ConversionTechnologyConfig,
)

from zen_europe.datasets.datasets import TYNDP2024Dataset


class PhotovoltaicsConfig(ConversionTechnologyConfig):
    """Configuration class for Photovoltaics."""

    name: str = "photovoltaics"


class Photovoltaics(ConversionTechnology):
    """Class containing all data and assumptions for photovoltaics."""

    name: str = "photovoltaics"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        return Attribute(name="input_carrier", default_value=[], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute(
            name="output_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """Returns standard baseline lifetime (no extension like fossils)."""
        return self.lifetime

    def _set_conversion_factor(self) -> Attribute:
        return self.conversion_factor

    def _get_capacity_limit(self) -> Attribute:
        """Overrides default to apply 2025/2030 limits directly."""
        attr = self.capacity_limit

        # Load TYNDP data
        tyndp_attr = TYNDP2024Dataset(self.source_path).get_capacity(
            element=self, target_year=2030
        )
        df_base = tyndp_attr.df.copy().reset_index()
        spatial_indices = [
            idx
            for idx in tyndp_attr.df.index.names
            if idx in ["location", "node", "edge"]
        ]

        # Create 2025 (0.0) and 2030 (1.3x) dataframe
        df_2025 = df_base[spatial_indices].drop_duplicates().copy()
        df_2025["year"] = 2025
        df_2025["capacity_limit"] = 0.0

        df_2030 = df_base[spatial_indices].copy()
        df_2030["year"] = 2030
        df_2030["capacity_limit"] = df_base["capacity_existing"].map(
            lambda x: x * 1.3 if x > 0 else 0.1
        )

        df_final = pd.concat([df_2025, df_2030], ignore_index=True).set_index(
            spatial_indices + ["year"]
        )

        attr.set_data(df=df_final, unit="GW", source=tyndp_attr.sources[0])
        return attr

    def _get_capacity_lower_limit(self) -> Attribute:
        """Overrides default to apply 2025/2030 lower limits."""
        attr = self.capacity_lower_limit

        tyndp_attr = TYNDP2024Dataset(self.source_path).get_capacity(
            element=self, target_year=2030
        )
        df_base = tyndp_attr.df.copy().reset_index()
        spatial_indices = [
            idx
            for idx in tyndp_attr.df.index.names
            if idx in ["location", "node", "edge"]
        ]

        df_2025 = df_base[spatial_indices].drop_duplicates().copy()
        df_2025["year"] = 2025
        df_2025["capacity_lower_limit"] = 0.0

        df_2030 = df_base[spatial_indices].copy()
        df_2030["year"] = 2030
        df_2030["capacity_lower_limit"] = df_base["capacity_existing"] * 0.7

        df_final = pd.concat([df_2025, df_2030], ignore_index=True).set_index(
            spatial_indices + ["year"]
        )

        attr.set_data(df=df_final, unit="GW", source=tyndp_attr.sources[0])
        return attr
