"""Aggregated technology cost database.

Combines capex/opex/efficiency/lifetime/construction-time figures from
several independent technology-cost sources (DEA, TYNDP, DIW, LUW, EUREF,
Potencia) into a single queryable database, following the same "many
agencies, one schema" approach as the legacy ``agg_financial_parameters.py``
script this class replaces.

"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Dict, cast

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Element

from zen_creator import (
    Attribute,
    ConversionTechnology,
    DatasetCollection,
    RetrofittingTechnology,
    StorageTechnology,
    Technology,
)
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.financial._cost_schema import (
    CO2_BASIS_UNITS,
    COST_VARIABLES,
    STANDARD_UNITS,
    YEARS,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.financial.diw import DIW
from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.datasets.datasets.financial.euref import EUREF
from zen_europe.datasets.datasets.financial.luw import LUW
from zen_europe.datasets.datasets.financial.potencia import Potencia
from zen_europe.datasets.datasets.financial.tyndp_technology_cost import (
    TYNDPTechnologyCost,
)
from zen_europe.datasets.datasets.technology.storage_technologies_schmidt import (
    StorageTechnologiesSchmidt,
)
from zen_europe.datasets.datasets.technology.storage_technologies_victoria import (
    StorageTechnologiesVictoria,
)

_AGENCY_DATASETS: dict[str, Callable[..., Dataset[Any]]] = {
    "dea": DEA,
    "tyndp": TYNDPTechnologyCost,
    "diw": DIW,
    "luw": LUW,
    "euref": EUREF,
    "potencia": Potencia,
    "schmidt": StorageTechnologiesSchmidt,
    "victoria": StorageTechnologiesVictoria,
}
_METRICS = ("mean", "median", "min", "max")

# A retrofit technology is sized by its retrofit reference carrier (the CO2 it
# captures), while the agencies report costs against the power capacity or
# energy throughput of the underlying plant. Dividing a cost by the retrofit
# flow coupling factor [tCO2/MWh] rebases it onto that CO2 basis; this maps the
# unit the agencies report to the (multiplier, resulting unit) of that division.
_RETROFIT_COUPLING_UNITS = ("tCO2eq/MWh", "tCO2/MWh")
_RETROFIT_UNIT_CONVERSION: dict[tuple[str, str], tuple[float, str]] = {
    ("capex", "Euro/kW"): (1e3, CO2_BASIS_UNITS["capex"]),
    ("fopex", "Euro/kW"): (1e3, CO2_BASIS_UNITS["fopex"]),
    ("vopex", "Euro/MWh"): (1.0, CO2_BASIS_UNITS["vopex"]),
}


class TechnologyCostDatabase(DatasetCollection):
    """Aggregated capex/opex/efficiency/lifetime technology cost database."""

    name = "technology_cost_database"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        self._rows_cache: dict[tuple[str, str, str | None], pd.DataFrame] = {}
        super().__init__(source_path=source_path)
        self._inflation = ECBInflation(source_path=self.source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available agency cost data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {name: cls(self.source_path) for name, cls in _AGENCY_DATASETS.items()}

    # -------- outward-facing accessors ------------------

    def get_capex_specific_conversion(
        self,
        element: ConversionTechnology,
        plant_size: str | None = None,
        metric: str = "mean",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Specific investment cost for `element`'s technology."""
        return self._set_technology_attribute(
            element,
            element.capex_specific_conversion,
            "capex",
            plant_size,
            metric,
            description="specific investment cost (CAPEX)",
            annual_values=True,
            proxy_element_name=proxy_element_name,
        )

    def get_opex_specific_fixed(
        self,
        element: Technology,
        plant_size: str | None = None,
        metric: str = "mean",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Fixed operational cost for `element`'s technology."""
        return self._set_technology_attribute(
            element,
            element.opex_specific_fixed,
            "fopex",
            plant_size,
            metric,
            description="fixed operational cost",
            annual_values=True,
            proxy_element_name=proxy_element_name,
        )

    def get_opex_specific_variable(
        self,
        element: Technology,
        plant_size: str | None = None,
        metric: str = "mean",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Variable operational cost for `element`'s technology."""
        return self._set_technology_attribute(
            element,
            element.opex_specific_variable,
            "vopex",
            plant_size,
            metric,
            description="variable operational cost",
            annual_values=False,
            proxy_element_name=proxy_element_name,
        )

    def get_capex_specific_storage(
        self,
        element: StorageTechnology,
        plant_size: str | None = None,
        metric: str = "mean",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Specific investment cost for `element`'s power capacity."""
        return self._set_technology_attribute(
            element,
            element.capex_specific_storage,
            "capex",
            plant_size,
            metric,
            description="specific investment cost (CAPEX) of the power capacity",
            annual_values=True,
            proxy_element_name=proxy_element_name,
        )

    def get_capex_specific_storage_energy(
        self,
        element: StorageTechnology,
        plant_size: str | None = None,
        metric: str = "mean",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Specific investment cost for `element`'s energy capacity."""
        return self._set_technology_attribute(
            element,
            element.capex_specific_storage_energy,
            "capex_energy",
            plant_size,
            metric,
            description="specific investment cost (CAPEX) of the energy capacity",
            annual_values=True,
            proxy_element_name=proxy_element_name,
        )

    def get_capex_specific_conversion_pyrolysis(
        self,
        element: ConversionTechnology,
        plant_size: str | None = None,
        metric: str = "mean",
    ) -> Attribute:
        """Specific investment cost for pyrolysis, per unit of reference carrier."""
        return self._set_technology_attribute(
            element,
            element.capex_specific_conversion,
            "capex",
            plant_size,
            metric,
            description="specific investment cost (CAPEX)",
            annual_values=True,
            multiplier=self._get_pyrolysis_multiplier(element),
        )

    def get_opex_specific_fixed_pyrolysis(
        self,
        element: ConversionTechnology,
        plant_size: str | None = None,
        metric: str = "mean",
    ) -> Attribute:
        """Fixed operational cost for pyrolysis, per unit of reference carrier."""
        return self._set_technology_attribute(
            element,
            element.opex_specific_fixed,
            "fopex",
            plant_size,
            metric,
            description="fixed operational cost",
            annual_values=True,
            multiplier=self._get_pyrolysis_multiplier(element),
        )

    def get_opex_specific_variable_pyrolysis(
        self,
        element: ConversionTechnology,
        plant_size: str | None = None,
        metric: str = "mean",
    ) -> Attribute:
        """Variable operational cost for pyrolysis, per unit of reference carrier."""
        return self._set_technology_attribute(
            element,
            element.opex_specific_variable,
            "vopex",
            plant_size,
            metric,
            description="variable operational cost",
            annual_values=False,
            multiplier=self._get_pyrolysis_multiplier(element),
        )

    def _get_pyrolysis_multiplier(self, element: ConversionTechnology) -> float:
        """Total pyrolysis output per unit of reference-carrier output.

        The agencies report the pyrolysis cost per MW of total output from the
        process, while the technology is sized by its reference carrier. The
        conversion factor gives the co-product outputs per unit of reference
        carrier, so summing them and adding the reference carrier itself gives
        the factor that rebases the cost onto the reference carrier.
        """
        reference_carrier = cast(list[str], element.reference_carrier.default_value)[0]
        conversion_factors = cast(
            list[dict[str, dict[str, float]]], element.conversion_factor.default_value
        )
        conversion_factor = {
            carrier: values["default_value"]
            for entry in conversion_factors
            for carrier, values in entry.items()
        }
        co_products = [
            carrier
            for carrier in cast(list[str], element.output_carrier.default_value)
            if carrier != reference_carrier
        ]
        return 1.0 + sum(conversion_factor[carrier] for carrier in co_products)

    def get_lifetime(
        self,
        element: Technology,
        plant_size: str | None = None,
        metric: str = "median",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Technical lifetime [years] for `element`'s technology."""
        return self._set_technology_attribute(
            element,
            element.lifetime,
            "lifetime",
            plant_size,
            metric,
            description="technical lifetime",
            annual_values=True,
            proxy_element_name=proxy_element_name,
            make_int=True,
        )

    def get_construction_time(
        self,
        element: Technology,
        plant_size: str | None = None,
        metric: str = "median",
        proxy_element_name: str | None = None,
    ) -> Attribute:
        """Construction time [years] for `element`'s technology."""
        return self._set_technology_attribute(
            element,
            element.construction_time,
            "construction_time",
            plant_size,
            metric,
            description="construction time",
            annual_values=True,
            proxy_element_name=proxy_element_name,
            make_int=True,
        )

    def get_efficiency(
        self,
        element: Element,
        plant_size: str | None = None,
        metric: str = "mean",
        reference_year: int | None = None,
    ) -> tuple[pd.Series, list[str]]:
        """Conversion efficiency [-] for `technology`, indexed by year.

        Returned directly as a `pd.Series` rather than an `Attribute`, since
        efficiency is technology-specific (e.g. it feeds a `conversion_factor`
        computation together with carrier-specific heating values) and has no
        single common attribute to populate across all conversion technologies.
        """
        data = self._aggregate(
            element.name,
            "efficiency",
            plant_size,
            metric,
            reference_year or self.settings.time.reference_year,
        )
        optimization_years = pd.Index(element.settings.time.years)
        data = self._reindex_to_years(data, optimization_years)
        agencies = self._extract_agencies(element.name, "efficiency", plant_size)
        assert not data.empty, (
            f"No efficiency data found for technology '{element.name}' "
            f"at plant size '{plant_size}' in any agency dataset."
        )
        return data, agencies

    def check_if_available(self, technology: str, variable: str | None = None) -> bool:
        """Whether any agency reports data for `technology` (optionally `variable`)."""
        for dataset in self.data.values():
            df = cast(Any, dataset).get_costs()
            if technology not in df.index.get_level_values("technology"):
                continue
            if variable is None:
                return True
            if variable in df.xs(technology, level="technology").index.get_level_values(
                "variable"
            ):
                return True
        return False

    def export_cost_table(
        self,
        path: Path,
        technologies: list[str] | None = None,
        plant_size: str | None = None,
        reference_year: int | None = None,
    ) -> pd.DataFrame:
        """Export a min/mean/max cost table (capex, fopex, vopex) to Excel.

        This is the numeric-export counterpart of the legacy script's
        `save_cost_curves`; the matplotlib `plot_cost_curves` figure export
        was intentionally not ported.
        """
        reference_year = reference_year or self.settings.time.reference_year
        if technologies is None:
            technologies = sorted(self._available_technologies())

        table: dict[tuple[str, str, str], pd.Series] = {}
        units: dict[tuple[str, str, str], str] = {}
        for technology in technologies:
            for variable in COST_VARIABLES:
                for metric in ("min", "mean", "max"):
                    series = self._aggregate(
                        technology, variable, plant_size, metric, reference_year
                    )
                    if series.empty:
                        continue
                    key = (technology, variable, metric)
                    table[key] = series
                    units[key] = self._unit_for(technology, variable, plant_size)
        cost_df = pd.DataFrame(table).T
        cost_df.index.names = ["technology", "variable", "metric"]
        cost_df.insert(0, "unit", pd.Series(units))
        cost_df.to_excel(path)
        return cost_df

    # -------- aggregation internals ------------------
    def _get_attribute_data(
        self,
        element: Element,
        attribute: Attribute,
        variable: str,
        plant_size: str | None,
        metric: str,
        description: str,
        annual_values: bool = True,
        proxy_element_name: str | None = None,
    ) -> tuple[pd.Series | None, float, pd.Series | None, list[str]]:
        """Get the data for a given attribute of a technology."""
        reference_year = element.settings.time.reference_year
        if proxy_element_name is not None:
            element_name = proxy_element_name
        else:
            element_name = element.name
        series = self._aggregate(
            element_name, variable, plant_size, metric, reference_year
        )
        agencies = self._extract_agencies(element_name, variable, plant_size)
        if series.empty:
            raise ValueError(
                f"No {description} data found for technology '{element_name}' "
                f"at plant size '{plant_size}' in any agency dataset."
            )

        optimization_years = pd.Index(element.settings.time.years)
        if not self.settings.cost.use_learning_curves:
            # the cost stays at the value of the reference year in all years
            default_value = float(
                self._reindex_to_years(series, pd.Index([reference_year])).loc[
                    reference_year
                ]
            )
            return None, default_value, None, agencies
        df: pd.Series | None
        yearly_variations: pd.Series | None
        if annual_values:
            df = self._reindex_to_years(series, optimization_years)
            default_value = float(df.loc[reference_year])
            if len(df.unique()) == 1:
                df = None
            else:
                df.index.name = "year"
                df.name = attribute.name
            yearly_variations = None
        else:
            default_value = float(
                self._reindex_to_years(series, pd.Index([reference_year])).loc[
                    reference_year
                ]
            )
            yearly_variations = (
                self._reindex_to_years(series, optimization_years) / default_value
            )
            yearly_variations.index.name = "year"
            yearly_variations.name = attribute.name
            df = None
        return df, default_value, yearly_variations, agencies

    def _set_technology_attribute(
        self,
        element: Element,
        attribute: Attribute,
        variable: str,
        plant_size: str | None,
        metric: str,
        description: str,
        annual_values: bool = True,
        multiplier: float = 1.0,
        make_int: bool = False,
        proxy_element_name: str | None = None,
    ) -> Attribute:
        df, default_value, yearly_variations, agencies = self._get_attribute_data(
            element,
            attribute,
            variable,
            plant_size,
            metric,
            description,
            annual_values,
            proxy_element_name=proxy_element_name,
        )
        default_value *= multiplier
        if df is not None:
            df = df * multiplier
        if make_int:
            default_value = int(np.round(default_value))
        # If the attribute is lifetime or construction_time, we don't want to provide a
        # df, since these are not time-varying attributes.
        if attribute.name == "lifetime" or attribute.name == "construction_time":
            df = None
        rebasing = (
            ""
            if multiplier == 1.0
            else (
                " The agencies report the cost per unit of total plant output, so it "
                "is rebased onto the reference carrier with a factor of "
                f"{multiplier:.4g}."
            )
        )
        if proxy_element_name is not None:
            add_desc_str = f" ('{proxy_element_name}' used as a proxy)"
            element_name = proxy_element_name
        else:
            add_desc_str = ""
            element_name = element.name
        source = SourceInformation(
            description=(
                f"{description.capitalize()} for '{element.name}'{add_desc_str} is the "
                f"{metric} across all available data for the agencies "
                f"{', '.join(agencies)} reporting data for this technology at plant "
                f"size '{plant_size}'. Monetary values are rebased to "
                f"{self.settings.time.price_year} "
                f"Euro using ECB HICP inflation.{rebasing}"
            ),
            metadata=self.metadata,
        )
        return attribute.set_data(
            source=source,
            default_value=default_value,
            df=df,
            unit=self._unit_for(element_name, variable, plant_size),
            yearly_variations_df=yearly_variations,
        )

    def _aggregate(
        self,
        technology: str,
        variable: str,
        plant_size: str | None,
        metric: str,
        reference_year: int,
    ) -> pd.Series:
        """Aggregate `variable` for `technology` across agencies/scenarios.

        Cost variables (capex/fopex/vopex) are inflation-adjusted to
        `reference_year` before aggregating; technology variables
        (efficiency/lifetime/construction_time) need no such adjustment.
        Returns a `pd.Series` indexed by year, empty if no agency has data.
        """
        if metric not in _METRICS:
            raise ValueError(f"metric must be one of {_METRICS}, got '{metric}'")

        rows = self._collect_rows(technology, variable, plant_size)
        if rows.empty:
            return pd.Series(dtype=float)

        if variable in COST_VARIABLES:
            rows = rows.assign(
                value=[
                    value
                    * self._inflation.get_inflation_rate(
                        int(money_year_src), self.settings.time.price_year
                    )
                    for value, money_year_src in zip(
                        rows["value"], rows["money_year_src"], strict=True
                    )
                ]
            )

        # one column per (agency, scenario) source series, interpolated over its own
        # reported years
        pivoted = rows.pivot_table(
            index="year", columns=["agency", "scenario"], values="value"
        )
        pivoted = pivoted.reindex(sorted(set(pivoted.index) | set(YEARS))).sort_index()
        pivoted = pivoted.interpolate(method="index", limit_direction="both")
        pivoted = pivoted.loc[pivoted.index.isin(YEARS)]

        ref_columns = [col for col in pivoted.columns if col[1] == "ref"]
        reference = (
            pivoted[ref_columns].mean(axis=1) if ref_columns else pivoted.mean(axis=1)
        )
        if metric == "min":
            candidate = (
                cast(pd.DataFrame, pivoted.xs("min", level="scenario", axis=1))
                if "min" in pivoted.columns.get_level_values("scenario")
                else pivoted[ref_columns]
            )
            result = candidate.min(axis=1)
            # guard against a reported "min" scenario that isn't actually below "ref"
            result = result.where(result <= reference, reference)
        elif metric == "max":
            candidate = (
                cast(pd.DataFrame, pivoted.xs("max", level="scenario", axis=1))
                if "max" in pivoted.columns.get_level_values("scenario")
                else pivoted[ref_columns]
            )
            result = candidate.max(axis=1)
            result = result.where(result >= reference, reference)
        elif metric == "median":
            result = pivoted.T.groupby(level="agency").median().median(axis=0)
        else:
            result = pivoted.T.groupby(level="agency").mean().mean(axis=0)
        result.index.name = "year"
        return result

    def _extract_agencies(
        self, technology: str, variable: str, plant_size: str | None
    ) -> list[str]:
        """Return the agencies reporting data for `technology`/`variable`.

        Sorted, because the agencies are rendered into the source descriptions
        that are written to disk.
        """
        rows = self._collect_rows(technology, variable, plant_size)
        return sorted(rows["agency"].unique())

    def _collect_rows(
        self, technology: str, variable: str, plant_size: str | None
    ) -> pd.DataFrame:
        """The rows every agency reports for `technology`/`variable`.

        The result is cached and shared between callers, so it must be
        treated as read-only.
        """
        key = (technology, variable, plant_size)
        if key not in self._rows_cache:
            self._rows_cache[key] = self._read_rows(technology, variable, plant_size)
        return self._rows_cache[key]

    def _read_rows(
        self, technology: str, variable: str, plant_size: str | None
    ) -> pd.DataFrame:
        frames = []
        for agency, dataset in self.data.items():
            df = cast(Any, dataset).get_costs()
            size: str | slice = slice(None) if plant_size is None else plant_size
            key = (technology, size, slice(None), variable, slice(None))
            try:
                sel = df.loc[key]
            except KeyError:
                continue
            if sel.empty:
                continue
            sel = sel.reset_index()
            sel["agency"] = agency
            frames.append(sel)
        if not frames:
            return pd.DataFrame(
                columns=["agency", "scenario", "year", "value", "money_year_src"]
            )
        return pd.concat(frames, ignore_index=True)

    def _unit_for(self, technology: str, variable: str, plant_size: str | None) -> str:
        """The unit actually reported for `technology`/`variable`.

        Most technologies use `STANDARD_UNITS[variable]`, but a few (DEA's
        carbon-capture technologies) report costs on a different physical
        basis (Euro/tCO2 rather than Euro/kW) -- the data itself is
        authoritative, `STANDARD_UNITS` is only a fallback for technologies
        with no data at all.
        """
        rows = self._collect_rows(technology, variable, plant_size)
        if rows.empty:
            return STANDARD_UNITS[variable]
        assert rows["unit"].nunique() == 1, (
            f"Multiple units reported for {variable} of {technology} at"
            f" plant size {plant_size}: {rows['unit'].unique()}"
        )
        return str(rows["unit"].iloc[0])

    def _available_technologies(self) -> set[str]:
        technologies: set[str] = set()
        for dataset in self.data.values():
            df = cast(Any, dataset).get_costs()
            technologies.update(df.index.get_level_values("technology"))
        return technologies

    @staticmethod
    def _reindex_to_years(series: pd.Series, years: pd.Index) -> pd.Series:
        combined_index = sorted(set(series.index) | set(years))
        reindexed = series.reindex(combined_index).interpolate(
            method="index", limit_direction="both"
        )
        return reindexed.loc[years]

    def get_capex_specific_conversion_retrofit(
        self,
        element: RetrofittingTechnology,
        base_technology: ConversionTechnology,
        plant_size: str = "M",
        metric: str = "mean",
    ) -> Attribute:
        """Specific investment cost for `element`'s retrofit technology."""
        return self._set_retrofit_cost_attribute(
            element,
            element.capex_specific_conversion,
            base_technology,
            "capex",
            plant_size,
            metric,
            description="specific investment cost (CAPEX)",
            annual_values=True,
        )

    def get_opex_specific_fixed_retrofit(
        self,
        element: RetrofittingTechnology,
        base_technology: ConversionTechnology,
        plant_size: str = "M",
        metric: str = "mean",
    ) -> Attribute:
        """Fixed operational cost for `element`'s retrofit technology."""
        return self._set_retrofit_cost_attribute(
            element,
            element.opex_specific_fixed,
            base_technology,
            "fopex",
            plant_size,
            metric,
            description="fixed operational cost",
            annual_values=True,
        )

    def get_opex_specific_variable_retrofit(
        self,
        element: RetrofittingTechnology,
        base_technology: ConversionTechnology,
        plant_size: str = "M",
        metric: str = "mean",
    ) -> Attribute:
        """Variable operational cost for `element`'s retrofit technology."""
        return self._set_retrofit_cost_attribute(
            element,
            element.opex_specific_variable,
            base_technology,
            "vopex",
            plant_size,
            metric,
            description="variable operational cost",
            annual_values=False,
        )

    def _annual_series(
        self,
        element: Element,
        variable: str,
        plant_size: str,
        metric: str,
        description: str,
    ) -> tuple[pd.Series, list[str]]:
        """Aggregated `variable` for `element`, on the optimization-year grid."""
        reference_year = element.settings.time.reference_year
        series = self._aggregate(
            element.name, variable, plant_size, metric, reference_year
        )
        if series.empty:
            raise ValueError(
                f"No {description} data found for technology '{element.name}' "
                f"at plant size '{plant_size}' in any agency dataset."
            )
        optimization_years = pd.Index(element.settings.time.years)
        return (
            self._reindex_to_years(series, optimization_years),
            self._extract_agencies(element.name, variable, plant_size),
        )

    def _set_retrofit_cost_attribute(
        self,
        element: RetrofittingTechnology,
        attribute: Attribute,
        base_technology: ConversionTechnology,
        variable: str,
        plant_size: str,
        metric: str,
        description: str,
        annual_values: bool = True,
    ) -> Attribute:
        """Set `attribute` to the cost of retrofitting `base_technology`.

        The agencies report the CCS-equipped plant and the base plant on the
        same power/energy basis, so the cost of the retrofit itself is the
        difference between the two. That difference is then divided by the
        retrofit flow coupling factor to express it per unit of captured CO2,
        which is what a retrofit technology is sized by.
        """
        series, agencies = self._annual_series(
            element, variable, plant_size, metric, f"{description} for retrofit"
        )
        series_base, agencies_base = self._annual_series(
            base_technology,
            variable,
            plant_size,
            metric,
            f"{description} for base technology",
        )

        reported_unit = self._unit_for(element.name, variable, plant_size)
        reported_unit_base = self._unit_for(base_technology.name, variable, plant_size)
        if reported_unit != reported_unit_base:
            raise ValueError(
                f"Cannot take a retrofit {variable} delta between "
                f"'{element.name}' ({reported_unit}) and '{base_technology.name}' "
                f"({reported_unit_base}): the two are reported on different bases."
            )

        delta = series - series_base
        if (delta <= 0).any():
            raise ValueError(
                f"Retrofitting '{base_technology.name}' to '{element.name}' has a "
                f"non-positive {description} delta in the year(s) "
                f"{list(delta.index[delta <= 0])}, which would give the retrofit "
                f"a zero or negative cost. Check the underlying agency data."
            )

        # rebase from the base plant's power/energy basis onto captured CO2
        coupling_factor = element.retrofit_flow_coupling_factor
        if coupling_factor.unit not in _RETROFIT_COUPLING_UNITS:
            raise ValueError(
                f"Expected the retrofit flow coupling factor of '{element.name}' "
                f"in one of {_RETROFIT_COUPLING_UNITS}, got "
                f"'{coupling_factor.unit}'."
            )
        if (variable, reported_unit) not in _RETROFIT_UNIT_CONVERSION:
            raise ValueError(
                f"No retrofit unit conversion defined for '{variable}' reported "
                f"as '{reported_unit}' (technology '{element.name}')."
            )
        multiplier, unit = _RETROFIT_UNIT_CONVERSION[(variable, reported_unit)]
        delta = delta / cast(float, coupling_factor.default_value) * multiplier

        reference_year = element.settings.time.reference_year
        at_reference_year = self._reindex_to_years(delta, pd.Index([reference_year]))
        default_value = float(at_reference_year.loc[reference_year])
        if not self.settings.cost.use_learning_curves:
            # the cost stays at the value of the reference year in all years
            df = None
            yearly_variations = None
        elif annual_values:
            # a delta that is flat across years is fully described by its default
            df = None if len(delta.unique()) == 1 else delta
            yearly_variations = None
        else:
            df = None
            yearly_variations = delta / default_value
        for frame in (df, yearly_variations):
            if frame is not None:
                frame.index.name = "year"
                frame.name = attribute.name

        agencies = sorted(set(agencies).union(agencies_base))
        source = SourceInformation(
            description=(
                f"{description.capitalize()} for '{element.name}' is the cost of "
                f"retrofitting '{base_technology.name}', i.e. the difference "
                f"between the two technologies' {metric} across all available "
                f"data for the agencies {', '.join(agencies)} reporting data at "
                f"plant size '{plant_size}', divided by the retrofit flow "
                f"coupling factor ({coupling_factor.default_value:.4g} "
                f"{coupling_factor.unit}) to express it per unit of captured "
                f"CO2. Monetary values are rebased to "
                f"{self.settings.time.price_year} Euro "
                f"using ECB HICP inflation."
            ),
            metadata=self.metadata,
        )
        return attribute.set_data(
            source=source,
            default_value=default_value,
            df=df,
            unit=unit,
            yearly_variations_df=yearly_variations,
        )
