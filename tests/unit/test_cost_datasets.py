"""Unit tests for the agency datasets of the technology cost database."""

from __future__ import annotations

from typing import cast

import pandas as pd
import pytest

from zen_europe.datasets.datasets.financial._cost_schema import SCENARIOS
from zen_europe.datasets.datasets.financial.euref import EUREF
from zen_europe.datasets.datasets.financial.luw import LUW

from .conftest import RAW_DATA_PATH

COST_PATH = RAW_DATA_PATH / "03-technology" / "cost"


def _select(costs: pd.DataFrame, technology: str, variable: str) -> pd.DataFrame:
    """The rows of `technology` and `variable`, indexed by scenario and year."""
    rows = costs.xs(
        (technology, "M", variable), level=("technology", "plant_size", "variable")
    )
    return cast(pd.DataFrame, rows)


@pytest.mark.skipif(
    not (COST_PATH / "luw").exists(), reason="the LUW cost data is not available"
)
def test_luw_methanation_vopex_is_converted_from_euro_per_kwh() -> None:
    """The source labels the methanation vopex €/MWh, but it is given in €/kWh."""
    vopex = _select(LUW(RAW_DATA_PATH).get_costs(), "methanation", "vopex")

    assert (vopex["unit"] == "Euro/MWh").all()
    assert (vopex["value"] == 1000 * vopex["value_src"]).all()


@pytest.mark.skipif(
    not (COST_PATH / "euref").exists(), reason="the EUREF cost data is not available"
)
class TestEUREF:
    def test_efficiency_follows_the_reported_years(self) -> None:
        """EUREF reports the efficiency of 2020, 2030, 2040 and 2050."""
        rows = _select(
            EUREF(RAW_DATA_PATH).get_costs(), "natural_gas_boiler_DH", "efficiency"
        )
        efficiency = cast(pd.Series, rows.xs("ref", level="scenario")["value"])

        assert list(efficiency.index) == [2020, 2030, 2040, 2050]
        assert efficiency[2030] > efficiency[2020]

    @pytest.mark.parametrize(
        "technology", ["rooftop_photovoltaics", "rooftop_photovoltaics_com"]
    )
    def test_rooftop_photovoltaics_has_every_scenario(self, technology: str) -> None:
        capex = _select(EUREF(RAW_DATA_PATH).get_costs(), technology, "capex")

        by_scenario = capex["value"].groupby(level="scenario").mean()
        assert set(by_scenario.index) == set(SCENARIOS)
        assert by_scenario["min"] < by_scenario["ref"] < by_scenario["max"]
