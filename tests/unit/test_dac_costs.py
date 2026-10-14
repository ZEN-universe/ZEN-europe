"""Unit tests for the DAC costs of Sievert et al. (2024) along global pathways."""

from __future__ import annotations

from typing import get_args

import numpy as np
import pandas as pd
import pytest
from zen_creator import Model
from zen_creator.utils.settings import Settings

import zen_europe.settings  # noqa: F401  (registers the categories)
from zen_europe.datasets.dataset_collections.dac_costs import DACCosts
from zen_europe.datasets.datasets.financial._cost_schema import CO2_BASIS_UNITS
from zen_europe.datasets.datasets.technology.DAC_capacities_zurbriggen import (
    DACCapacitiesZurbriggen,
)
from zen_europe.datasets.datasets.technology.DAC_costs_sievert import (
    DACCostsSievert,
)
from zen_europe.elements.conversion_technologies.DAC import DAC
from zen_europe.settings.cost import DACDeploymentPathway, DACTechnology
from zen_europe.utils.constants import Constants

from .conftest import RAW_DATA_PATH

pytestmark = pytest.mark.skipif(
    not (RAW_DATA_PATH / "03-technology" / "cost" / "sievert").exists(),
    reason="the cached cost curves of Sievert et al. are not available",
)

COST_ATTRIBUTES = {
    "capex": "capex_specific_conversion",
    "fopex": "opex_specific_fixed",
    "vopex": "opex_specific_variable",
}


def _dac(model: Model, **cost_settings: object) -> DAC:
    """A DAC element whose cost settings are overridden by `cost_settings`."""
    model.settings = Settings.model_validate({"cost": cost_settings})
    return DAC(model=model)


def _build(dac: DAC, variable: str):
    """Build and return the cost attribute of `variable`."""
    name = COST_ATTRIBUTES[variable]
    dac._build_attribute(name)
    return getattr(dac, name)


def _cost_by_year(attribute) -> pd.Series:
    """The cost of every year, from either the df or the yearly variation."""
    if attribute.df is not None:
        return attribute.df
    return attribute.yearly_variations_df * attribute.default_value


def _dac_costs(model: Model) -> DACCosts:
    return DACCosts(settings=model.settings, source_path=model.source_path)


def test_settings_match_the_datasets() -> None:
    """Every pathway and technology of the settings exists in a dataset."""
    pathways = {DACCosts.IEA_PATHWAY} | set(
        DACCapacitiesZurbriggen.GLOBAL_CAPACITY_PATHWAYS
    )
    assert set(get_args(DACDeploymentPathway)) == pathways
    assert set(get_args(DACTechnology)) == set(DACCostsSievert.TECHNOLOGIES)


@pytest.mark.parametrize("variable", list(COST_ATTRIBUTES))
def test_units_are_on_a_co2_basis(model: Model, variable: str) -> None:
    attribute = _build(_dac(model), variable)

    assert attribute.unit == CO2_BASIS_UNITS[variable]


@pytest.mark.parametrize("pathway", get_args(DACDeploymentPathway))
@pytest.mark.parametrize("variable", list(COST_ATTRIBUTES))
def test_cost_declines_with_the_year(model: Model, pathway: str, variable: str) -> None:
    """The global capacity grows in every pathway, so the cost never rises."""
    cost = _cost_by_year(_build(_dac(model, dac_deployment_pathway=pathway), variable))

    assert (np.diff(cost.to_numpy()) <= 1e-9 * cost.max()).all()
    assert cost.iloc[-1] < cost.iloc[0]


@pytest.mark.parametrize("variable", list(COST_ATTRIBUTES))
def test_cost_is_flat_without_learning_curves(model: Model, variable: str) -> None:
    dac = _dac(model, use_learning_curves=False)
    attribute = _build(dac, variable)

    assert attribute.df is None
    assert attribute.yearly_variations_df is None
    reference_year = model.settings.time.reference_year
    with_learning = _build(_dac(model), variable)
    assert attribute.default_value == pytest.approx(
        _cost_by_year(with_learning).loc[reference_year]
    )


@pytest.mark.parametrize("variable", list(COST_ATTRIBUTES))
def test_default_is_the_curve_at_the_reference_year_capacity(
    model: Model, variable: str
) -> None:
    dac = _dac(model)
    attribute = _build(dac, variable)
    dataset = DACCostsSievert(source_path=model.source_path)

    settings = model.settings
    reference_year = settings.time.reference_year
    capacity = _dac_costs(model).get_global_capacity(
        settings.cost.dac_deployment_pathway, [reference_year]
    )
    cost_usd = dataset.get_cost_at_capacity(
        settings.cost.dac_technology, variable, capacity.to_numpy()
    )[0]
    hours = Constants.HOURS_PER_YEAR if variable in ("capex", "fopex") else 1.0
    expected = cost_usd * hours * dataset._usd_to_euro(reference_year)

    assert attribute.default_value == pytest.approx(expected)


def test_vopex_excludes_energy_and_co2_transport_and_storage(model: Model) -> None:
    """
    At its first-commercial plant scale, the variable opex of liquid solvent is
    only water and chemicals; the CO2 transport (4.5 $/t) and storage (about 19 $/t)
    of Sievert et al. are excluded.
    """
    dataset = DACCostsSievert(source_path=model.source_path)
    scale = DACCostsSievert.TECHNOLOGIES["liquid_solvent"]["scale"]

    vopex = dataset.get_cost_at_capacity("liquid_solvent", "vopex", np.array([scale]))

    water = DACCostsSievert.WATER_DEMAND["liquid_solvent"] * DACCostsSievert.WATER_PRICE
    chemicals = DACCostsSievert.CHEMICALS["liquid_solvent"]
    assert vopex[0] == pytest.approx(water + chemicals)


def test_interpolation_at_a_grid_node_returns_the_node(model: Model) -> None:
    dataset = DACCostsSievert(source_path=model.source_path)
    curve = dataset.data["solid_sorbent|capex|p50"]

    nodes = curve.index.to_numpy()[[0, 40, 100, -1]]
    values = dataset.get_cost_at_capacity("solid_sorbent", "capex", nodes)

    np.testing.assert_array_equal(values, curve.loc[nodes].to_numpy())


@pytest.mark.parametrize(
    ("pathway", "expected"),
    [
        ("IEA NZE 2050", [80e6, 1041e6]),
        ("wind + policy", [88e6, 1600e6]),
    ],
)
def test_global_capacity_hits_the_anchors(
    model: Model, pathway: DACDeploymentPathway, expected: list[float]
) -> None:
    """The pathway starts from the operational projects of Zurbriggen et al."""
    dac_costs = _dac_costs(model)
    operational = dac_costs._zurbriggen.get_global_dac_capacity_operational()
    first_year = int(operational.index.max())

    capacity = dac_costs.get_global_capacity(pathway, [first_year, 2030, 2050])

    np.testing.assert_allclose(
        capacity.to_numpy(), [operational.loc[first_year], *expected]
    )


@pytest.mark.parametrize("source", ["sievert", "tech_db"])
def test_dac_cost_source_selects_the_dataset(model: Model, source: str) -> None:
    attribute = _build(_dac(model, dac_cost_source=source), "capex")

    description = attribute.sources[-1].description
    assert ("Sievert et al." in description) == (source == "sievert")
