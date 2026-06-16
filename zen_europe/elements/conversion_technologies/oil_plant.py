from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import pandas as pd
from zen_creator import (
    Attribute,
    ConversionTechnologyConfig,
    GenericConversionTechnology,
)

from zen_europe.datasets.datasets import EntsoePPDataset, TYNDP2024Dataset


class OilPlantConfig(ConversionTechnologyConfig):
    name: str = "oil_plant"
    use_entsoe_existing_capacities: bool = True


class OilPlant(GenericConversionTechnology):
    name: str = "oil_plant"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_lifetime(self) -> Attribute:
        """Extends lifetime by +10 years to prevent early retirements."""
        attr = self.lifetime
        if attr.default_value is not None:
            attr.default_value = float(attr.default_value + 10)
        return attr

    def _set_capacity_existing(self) -> Attribute:
        attr = self.capacity_existing
        if (
            self.model.config.data.conversion_technology.oil_plant.use_entsoe_existing_capacities
        ):
            attr = EntsoePPDataset(self.source_path).get_capacity(element=self)
        return attr

    def _set_capacity_limit(self) -> Attribute:
        return self._build_combined_limits(bound_type="upper")

    def _set_capacity_lower_limit(self) -> Attribute:
        return self._build_combined_limits(bound_type="lower")

    def _build_combined_limits(self, bound_type: str) -> Attribute:
        """Helper method to construct the 2025 and 2030 capacity bounds."""
        entsoe_attr = self._set_capacity_existing()
        spatial_indices = [
            idx
            for idx in entsoe_attr.df.index.names
            if idx in ["location", "node", "edge"]
        ]

        df_2025_base = entsoe_attr.df.copy().reset_index()
        locs_2025 = (
            df_2025_base[spatial_indices].drop_duplicates()
            if not df_2025_base.empty
            else pd.DataFrame(columns=spatial_indices)
        )

        try:
            tyndp_attr = TYNDP2024Dataset(self.source_path).get_capacity(
                element=self, target_year=2030
            )
            df_2030_base = tyndp_attr.df.copy().reset_index()
        except Exception:
            df_2030_base = pd.DataFrame()

        locs_2030 = (
            df_2030_base[spatial_indices].drop_duplicates()
            if not df_2030_base.empty
            else pd.DataFrame(columns=spatial_indices)
        )
        all_locs = pd.concat([locs_2025, locs_2030]).drop_duplicates()

        # 2025 Limit (Set to 0)
        df_2025 = all_locs.copy()
        df_2025["year"] = 2025

        if bound_type == "upper":
            df_2025["capacity_limit"] = 0.0
            attr, col_name = self.capacity_limit, "capacity_limit"
        else:
            df_2025["capacity_lower_limit"] = 0.0
            attr, col_name = self.capacity_lower_limit, "capacity_lower_limit"

        # 2030 Limits
        if not df_2030_base.empty:
            df_2030 = df_2030_base[spatial_indices].copy()
            df_2030["year"] = 2030
            if bound_type == "upper":
                df_2030[col_name] = df_2030_base["capacity_existing"].map(
                    lambda x: x * 1.3 if x > 0 else 0.1
                )
            else:
                df_2030[col_name] = df_2030_base["capacity_existing"] * 0.7
            df_combined = pd.concat([df_2025, df_2030], ignore_index=True)
            source = tyndp_attr.sources[0]
        else:
            df_combined = df_2025
            source = entsoe_attr.sources[0]

        df_combined.set_index(spatial_indices + ["year"], inplace=True)
        attr.set_data(df=df_combined, unit="GW", source=source)
        return attr
