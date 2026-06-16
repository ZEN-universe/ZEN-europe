from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, ConversionTechnologyConfig

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

    def _set_capacity_limit(self) -> Attribute:
        """Builds combined upper limits
        (2025 = 0, 2030 = 130% TYNDP or 0.1 fallback)."""
        return self._build_combined_limits(bound_type="upper")

    def _set_capacity_lower_limit(self) -> Attribute:
        """Builds combined lower limits (2025 = 0, 2030 = 70% TYNDP)."""
        return self._build_combined_limits(bound_type="lower")

    def _build_combined_limits(self, bound_type: str) -> Attribute:
        """Constructs the 2025 and 2030 capacity bounds
        purely from TYNDP for PV."""
        # For PV, get spatial indices from TYNDP directly
        # since it skips ENTSO-E existing capacities
        try:
            tyndp_attr = TYNDP2024Dataset(self.source_path).get_capacity(
                element=self, target_year=2030
            )
            df_2030_base = tyndp_attr.df.copy().reset_index()
            spatial_indices = [
                idx
                for idx in tyndp_attr.df.index.names
                if idx in ["location", "node", "edge"]
            ]
        except Exception:
            df_2030_base = pd.DataFrame()
            spatial_indices = ["node"]  # Default safety fallback if dataset is empty

        locs_2030 = (
            df_2030_base[spatial_indices].drop_duplicates()
            if not df_2030_base.empty
            else pd.DataFrame(columns=spatial_indices)
        )

        # 1. Build 2025 Limits (All zeros)
        df_2025 = locs_2030.copy()
        df_2025["year"] = 2025

        if bound_type == "upper":
            df_2025["capacity_limit"] = 0.0
            attr, col_name = self.capacity_limit, "capacity_limit"
        else:
            df_2025["capacity_lower_limit"] = 0.0
            attr, col_name = self.capacity_lower_limit, "capacity_lower_limit"

        # 2. Build 2030 Limits
        if not df_2030_base.empty:
            df_2030 = df_2030_base[spatial_indices].copy()
            df_2030["year"] = 2030
            if bound_type == "upper":
                # If capacity existing > 0, multiply by 1.3, else default to 0.1 penalty
                df_2030[col_name] = df_2030_base["capacity_existing"].map(
                    lambda x: x * 1.3 if x > 0 else 0.1
                )
            else:
                df_2030[col_name] = df_2030_base["capacity_existing"] * 0.7

            df_combined = pd.concat([df_2025, df_2030], ignore_index=True)
            source = tyndp_attr.sources[0]
        else:
            df_combined = df_2025
            source = None  # Handle edge cases gracefully

        df_combined.set_index(spatial_indices + ["year"], inplace=True)
        attr.set_data(df=df_combined, unit="GW", source=source)
        return attr
