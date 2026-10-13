from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial._cost_schema import CO2_BASIS_UNITS
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.settings.cache import get_active_cache_settings
from zen_europe.settings.cost import DACTechnology
from zen_europe.utils.constants import Constants

# cost items of one technology, one array of Monte Carlo draws per item
_Items = dict[str, np.ndarray]


class DACCostsSievert(Dataset[pd.DataFrame]):
    """
    Cost of direct air capture from the experience curves of Sievert et al. (2024).

    Sievert et al. project the capex (total overnight cost), the fixed opex and
    the variable opex of three DAC technologies (liquid solvent, solid sorbent,
    CaO ambient weathering) as a function of the cumulative global DAC
    capacity. Every cost item carries its own experience rate, drawn from the
    distribution that the expert interviews of the paper imply for it. The
    reconstruction of the model from the supplemental information (tables S6,
    S7, S9-S16, S19-S21) reproduces the published results within a few percent.

    The model is a Monte Carlo simulation. It is not run at model build time:
    `_set_data` reads the cost curves (5th, 50th and 95th percentile against the
    cumulative global capacity) from a cache file and only runs the Monte Carlo
    simulation when the cache is missing or `cache.overwrite_dac_costs_sievert`
    is set. The model uses the median.

    The dataset gives the cost at a cumulative global capacity. Which capacity
    is reached in which year is not part of Sievert et al.; the dataset collection
    `DACCosts` combines the cost curves with a deployment pathway.

    Two parts of the variable opex of Sievert et al. are excluded, because they
    are modeled elsewhere in ZEN-europe:

    - Electricity and heat. DAC consumes the input carriers electricity and
      heat, which are priced by the model.
    - CO2 transport and storage. The captured CO2 is stored by the technology
      `carbon_storage`, which has its own costs. This removes about 90% of the
      non-energy variable opex of liquid solvent and 96% of CaO ambient
      weathering, but only about 14% of solid sorbent, whose variable opex is
      dominated by water and sorbent replacement.

    """

    name = "dac_costs_sievert"

    CACHE_FILE = "dac_cost_curve_sievert.csv"
    MONEY_YEAR = 2022
    PERCENTILE = "p50"
    PERCENTILES = (5, 50, 95)

    # -------- Monte Carlo simulation ------------------------
    N_DRAWS = 250_000
    # seeds of the capital and of the variable opex draws
    SEED_CAPITAL = 20260213
    SEED_VARIABLE = 71452
    # cumulative global capacity [tCO2/yr] the curves are evaluated at; the
    # first-commercial plant scales are added so the kink there is exact
    CAPACITY_GRID = np.geomspace(1_000, 5e9, 161)

    # Technology types of Malhotra & Schmidt (2020): mean and standard deviation
    # of the experience rate of each type (table S6, figure 1B).
    TYPE_MEAN = np.array([0.22, 0.13, 0.05])
    TYPE_SD = np.array([0.043, 0.044, 0.052])
    # Probabilities of the three technology types from the expert interviews
    # (table S6). The experience rate is drawn from the implied Gaussian mixture.
    TYPE_PROBABILITIES: dict[str, list[float]] = {
        "ls_contactor": [0.286, 0.643, 0.071],
        "ls_pellet": [0.167, 0.625, 0.208],
        "ls_slaker": [0.333, 0.500, 0.167],
        "ls_calciner": [0.071, 0.571, 0.357],
        "ls_system": [0.000, 0.333, 0.667],
        "ss_contactor": [0.077, 0.923, 0.000],
        "ss_system": [0.000, 0.857, 0.143],
        "cao_contactor": [0.200, 0.700, 0.100],
        "cao_kiln": [0.000, 0.800, 0.200],
        "cao_system": [0.143, 0.786, 0.071],
    }
    # Triangular experience rates (min, mode, max): off-the-shelf components and
    # variable opex (tables S7, S8), and the sorbent, after bulk polymers (table S7).
    NON_NOVEL_EXPERIENCE_RATE = (0.0, 0.025, 0.05)
    SORBENT_EXPERIENCE_RATE = (0.18, 0.275, 0.37)

    # Direct materials cost [M$2022] at the first-commercial plant scale, as
    # (lower bound, upper bound, experience rate), and the plant parameters.
    TECHNOLOGIES: dict[str, dict] = {
        "liquid_solvent": {
            "scale": 500_000,  # tCO2/yr, table S9
            "installation": 187.0 / 299.0,  # of direct materials, table S10
            "process_contingency": (0.30, 0.70),  # table S16
            "system": "ls_system",
            "direct_materials": {  # table S10
                "Air contactor": (89.0, 177.0, "ls_contactor"),
                "Pellet reactor": (63.0, 95.0, "ls_pellet"),
                "Slaker": (12.0, 17.0, "ls_slaker"),
                "Calciner": (20.0, 41.0, "ls_calciner"),
                "Other equipment": (50.0, 84.0, "non_novel"),
                "Air separation unit": (31.0, 48.0, "non_novel"),
                "Fines filter": (15.0, 25.0, "non_novel"),
                "Compressor": (10.0, 10.0, "non_novel"),
                "Steam turbine": (7.0, 7.0, "non_novel"),
                "Buildings and land": (2.0, 2.0, "non_novel"),
            },
        },
        "solid_sorbent": {
            "scale": 4_000,  # tCO2/yr, table S9
            "installation": 1.5 / 12.0,  # table S12
            "process_contingency": (0.05, 0.20),  # table S16
            "system": "ss_system",
            "direct_materials": {  # table S12
                "Air contactors": (3.7, 3.7, "ss_contactor"),
                "Blowers": (0.1, 0.1, "ss_contactor"),
                "Switching valves": (3.4, 3.4, "ss_contactor"),
                "Initial sorbent": (0.5, 0.5, "ss_sorbent"),
                "Vacuum pump 1": (0.2, 0.2, "non_novel"),
                "Vacuum pump 2": (0.1, 0.1, "non_novel"),
                "Gas storage balloon": (0.02, 0.02, "non_novel"),
                "Condensers": (0.4, 0.4, "non_novel"),
                "Compressor": (2.6, 2.6, "non_novel"),
                "Buildings and land": (1.0, 1.0, "non_novel"),
            },
        },
        "cao_weathering": {
            "scale": 1_000,  # tCO2/yr, table S9
            "installation": 0.2 / 5.8,  # table S14
            "process_contingency": (0.20, 0.35),  # table S16
            "system": "cao_system",
            "direct_materials": {  # table S14
                "Air contactor structure": (2.4, 2.4, "cao_contactor"),
                "Electric kiln (calciner)": (2.4, 3.6, "cao_kiln"),
                "Compressor": (0.3, 0.3, "non_novel"),
                "Conveyors": (0.3, 0.3, "non_novel"),
                "Buildings and land": (0.2, 0.2, "non_novel"),
                "Other equipment": (0.2, 0.2, "non_novel"),
                "Raw materials (CaO)": (0.002, 0.002, "non_novel"),
            },
        },
    }

    # Total overnight cost build-up (table S15). Start-up labour, fuel and
    # chemicals are omitted, about 0.7% of the total overnight cost (table S32).
    EPC_FACTOR = 0.15  # of direct materials and installation
    PROJECT_CONTINGENCY = 0.35  # of the total EPC cost
    OWNERS_COST = 0.07  # of the total plant cost
    SPARE_PARTS = 0.005  # of the total plant cost
    STARTUP_CAPITAL = 0.02  # of the total plant cost

    # Fixed opex (table S19)
    EMPLOYEES_PER_MT = 278  # employees of a 1 MtCO2/yr plant, scaled linearly
    OPERATOR_SALARY = 72_186  # $2022 per employee and year
    MAINTENANCE = 0.015  # of the total plant cost
    INDIRECT_LABOUR = 0.30  # of direct labour and maintenance
    INSURANCE = 0.005  # of the total plant cost
    TAXES_AND_FEES = 0.005  # of the total plant cost

    # Variable opex without energy, CO2 transport and CO2 storage (tables S20, S21)
    WATER_PRICE = 0.21  # $/m3
    WATER_DEMAND = {  # m3/tCO2
        "liquid_solvent": 4.8,
        "solid_sorbent": 410.0,
        "cao_weathering": 0.0,
    }
    CHEMICALS = {"liquid_solvent": 1.4, "cao_weathering": 1.0}  # $/tCO2
    # Solid sorbent replacement: 57.5 t of sorbent at 8,821 $/t for a plant of
    # 4,000 tCO2/yr, replaced every 1-3 years (uniform). The cost of the longest
    # lifetime is a floor that learning does not go below (table S21).
    SORBENT_COST_ONE_YEAR = 57.5 * 8_821 / 4_000  # $/tCO2
    SORBENT_LIFETIME = (1.0, 3.0)  # years

    # unit of each cost variable in the cost curves
    SOURCE_UNITS = {
        "capex": "USD/(tCO2/yr)",
        "fopex": "USD/(tCO2/yr)/yr",
        "vopex": "USD/tCO2",
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Considering technology characteristics to project future costs "
                "of direct air capture"
            ),
            author=["Katrin Sievert", "Tobias S. Schmidt", "Bjarne Steffen"],
            publication="Joule",
            publication_year=2024,
            doi="https://doi.org/10.1016/j.joule.2024.02.005",
            note=(
                "Reconstructed from the supplemental tables S6, S7, S9-S16 and "
                "S19-S21. Cost curves are the median of a Monte Carlo simulation "
                "against the cumulative global DAC capacity. Electricity, heat, CO2 "
                "transport and CO2 storage are excluded from the variable opex."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        path = Path(self.source_path) / "03-technology" / "cost" / "sievert"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _set_data(self) -> pd.DataFrame:
        """
        The cost curves in US$2022 against the cumulative global capacity.

        The columns are named `<technology>|<variable>|<percentile>`, the index
        is the cumulative global capacity [tCO2/yr].
        """
        cache_path = self.path / self.CACHE_FILE
        overwrite = get_active_cache_settings().overwrite_dac_costs_sievert
        if cache_path.exists() and not overwrite:
            return pd.read_csv(cache_path, index_col=0, float_precision="round_trip")
        data = self._generate_cost_curves()
        data.to_csv(cache_path)
        return data

    # -------- methods ------------------------
    def get_cost(
        self,
        technology: DACTechnology,
        variable: str,
        capacity: np.ndarray,
        reference_year: int,
    ) -> np.ndarray:
        """
        Median cost of `variable` at the cumulative global `capacity` [tCO2/yr],
        in Euro of `reference_year` and the units of `get_unit`.

        The capex and the fixed opex are converted from per tCO2/yr to per tCO2/h
        of nameplate capacity. No capacity factor is applied: both are costs per
        unit of capacity, independent of how much the plant is used.
        """
        cost = self.get_cost_at_capacity(technology, variable, capacity)
        if variable in ("capex", "fopex"):
            cost = cost * Constants.HOURS_PER_YEAR  # per tCO2/yr -> per tCO2/h
        return cost * self._usd_to_euro(reference_year)

    @staticmethod
    def get_unit(variable: str) -> str:
        """The unit of `variable` returned by `get_cost`."""
        return CO2_BASIS_UNITS[variable]

    def get_cost_at_capacity(
        self, technology: DACTechnology, variable: str, capacity: np.ndarray
    ) -> np.ndarray:
        """
        Median cost [US$2022, `SOURCE_UNITS`] at the cumulative global `capacity`.

        The cost curve is interpolated linearly in log capacity. Below the
        first-commercial plant scale of a technology the curve is flat, since no
        learning is credited there.
        """
        curve = self.data[f"{technology}|{variable}|{self.PERCENTILE}"]
        return np.interp(
            np.log(np.asarray(capacity, dtype=float)),
            np.log(curve.index.to_numpy(dtype=float)),
            curve.to_numpy(dtype=float),
        )

    # -------- helpers ------------------------
    def _usd_to_euro(self, reference_year: int) -> float:
        """Factor from US$ of `MONEY_YEAR` to Euro of `reference_year`."""
        dollar2euro = ECBDollar2Euro(source_path=self.source_path)
        inflation = ECBInflation(source_path=self.source_path)
        return dollar2euro.get_dollar2euro(self.MONEY_YEAR) * (
            inflation.get_inflation_rate(self.MONEY_YEAR, reference_year)
        )

    # -------- Monte Carlo simulation ------------------------
    def _generate_cost_curves(self) -> pd.DataFrame:
        """
        Run the Monte Carlo simulation and return the cost curves.

        The draws of each technology are reused for every capacity of the grid,
        so the curves are monotonic in capacity. The draws are reproducible with
        the two seeds, provided the technologies are drawn in the same order.
        """
        rng_capital = np.random.default_rng(self.SEED_CAPITAL)
        rng_variable = np.random.default_rng(self.SEED_VARIABLE)
        scales = [technology["scale"] for technology in self.TECHNOLOGIES.values()]
        grid = np.unique(np.concatenate([self.CAPACITY_GRID, np.array(scales, float)]))

        curves: dict[str, np.ndarray] = {}
        for technology, parameters in self.TECHNOLOGIES.items():
            n = self.N_DRAWS
            capex, capex_rates = self._draw_capex_items(technology, n, rng_capital)
            fopex, fopex_rates = self._fixed_opex_items(capex, capex_rates)
            vopex, vopex_rates, floors = self._draw_variable_opex_items(
                technology, n, rng_variable
            )
            for variable, items, rates, item_floors in (
                ("capex", capex, capex_rates, {}),
                ("fopex", fopex, fopex_rates, {}),
                ("vopex", vopex, vopex_rates, floors),
            ):
                values = np.array(
                    [
                        np.percentile(
                            self._project(
                                items, rates, capacity, parameters["scale"], item_floors
                            ),
                            self.PERCENTILES,
                        )
                        for capacity in grid
                    ]
                )
                for i, percentile in enumerate(self.PERCENTILES):
                    curves[f"{technology}|{variable}|p{percentile}"] = values[:, i]
        data = pd.DataFrame(curves, index=pd.Index(grid, name="capacity_tCO2_per_yr"))
        return data

    def _draw_experience_rates(
        self, n: int, rng: np.random.Generator
    ) -> dict[str, np.ndarray]:
        """Draw the experience rates of every experience-rate category."""
        rates = {}
        for category, probabilities in self.TYPE_PROBABILITIES.items():
            p = np.asarray(probabilities, dtype=float)
            types = rng.choice(3, size=n, p=p / p.sum())
            rate = rng.normal(self.TYPE_MEAN[types], self.TYPE_SD[types])
            rates[category] = np.clip(rate, 0.0, 0.95)
        rates["non_novel"] = rng.triangular(*self.NON_NOVEL_EXPERIENCE_RATE, size=n)
        rates["ss_sorbent"] = rng.triangular(*self.SORBENT_EXPERIENCE_RATE, size=n)
        return rates

    def _draw_capex_items(
        self, technology: str, n: int, rng: np.random.Generator
    ) -> tuple[_Items, _Items]:
        """
        Draw the total overnight cost items [$/(tCO2/yr)] at the first-commercial
        plant scale and their experience rates.

        The direct materials take the experience rate of their component, all
        cost items derived from them the system-level experience rate.
        """
        parameters = self.TECHNOLOGIES[technology]
        scale = parameters["scale"]
        experience_rates = self._draw_experience_rates(n, rng)
        system_rate = experience_rates[parameters["system"]]

        items: _Items = {}
        rates: _Items = {}
        direct_materials = np.zeros(n)
        for component, (low, high, category) in parameters["direct_materials"].items():
            cost = rng.uniform(low, high, n) if high > low else np.full(n, low)
            items[component] = cost * 1e6 / scale  # M$ -> $/(tCO2/yr)
            rates[component] = experience_rates[category]
            direct_materials += items[component]

        installation = direct_materials * parameters["installation"]
        epc = self.EPC_FACTOR * (direct_materials + installation)
        total_epc_cost = direct_materials + installation + epc
        project_contingency = self.PROJECT_CONTINGENCY * total_epc_cost
        low, high = parameters["process_contingency"]
        process_contingency = rng.uniform(low, high, n) * total_epc_cost
        total_plant_cost = total_epc_cost + project_contingency + process_contingency
        derived = {
            "Installation": installation,
            "Engineering & procurement": epc,
            "Project contingency": project_contingency,
            "Process contingency": process_contingency,
            "Owner's cost": self.OWNERS_COST * total_plant_cost,
            "Spare parts": self.SPARE_PARTS * total_plant_cost,
            "Start-up capital": self.STARTUP_CAPITAL * total_plant_cost,
        }
        for item, cost in derived.items():
            items[item] = cost
            rates[item] = system_rate
        return items, rates

    def _fixed_opex_items(
        self, capex: _Items, capex_rates: _Items
    ) -> tuple[_Items, _Items]:
        """
        The fixed opex items [$/(tCO2/yr)/yr] at the first-commercial plant scale.

        All items take the system-level experience rate, since Sievert et al.
        assume that the fixed opex falls with the capital cost (table S7).
        """
        excluded = ("Owner's cost", "Spare parts", "Start-up capital")
        total_plant_cost = sum(
            (cost for item, cost in capex.items() if item not in excluded),
            start=np.zeros_like(capex["Installation"]),
        )
        system_rate = capex_rates["Project contingency"]
        direct_labour = np.full_like(
            total_plant_cost, self.EMPLOYEES_PER_MT / 1e6 * self.OPERATOR_SALARY
        )
        maintenance = self.MAINTENANCE * total_plant_cost
        items: _Items = {
            "Direct labour": direct_labour,
            "Maintenance": maintenance,
            "Indirect labour": self.INDIRECT_LABOUR * (direct_labour + maintenance),
            "Insurance": self.INSURANCE * total_plant_cost,
            "Local taxes and fees": self.TAXES_AND_FEES * total_plant_cost,
        }
        return items, {item: system_rate for item in items}

    def _draw_variable_opex_items(
        self, technology: str, n: int, rng: np.random.Generator
    ) -> tuple[_Items, _Items, dict[str, float]]:
        """
        Draw the variable opex items [$/tCO2] at the first-commercial plant scale,
        their experience rates and their cost floors.

        Electricity, heat, CO2 transport and CO2 storage are not included. All
        items take the triangular experience rate of variable opex (table S7).
        """
        items: _Items = {
            "Water": np.full(n, self.WATER_DEMAND[technology] * self.WATER_PRICE)
        }
        floors: dict[str, float] = {}
        if technology == "solid_sorbent":
            lifetime = rng.uniform(*self.SORBENT_LIFETIME, n)
            items["Sorbent replacement"] = self.SORBENT_COST_ONE_YEAR / lifetime
            floors["Sorbent replacement"] = (
                self.SORBENT_COST_ONE_YEAR / self.SORBENT_LIFETIME[1]
            )
        else:
            items["Chemicals"] = np.full(n, self.CHEMICALS[technology])
        rate = rng.triangular(*self.NON_NOVEL_EXPERIENCE_RATE, size=n)
        return items, {item: rate for item in items}, floors

    @staticmethod
    def _project(
        items: _Items,
        rates: _Items,
        capacity: float,
        scale: float,
        floors: Mapping[str, float],
    ) -> np.ndarray:
        """
        Total cost at the cumulative `capacity` (multi-component experience curve,
        equations 4-5 of Sievert et al.). Below the first-commercial plant
        `scale` no learning is credited.
        """
        ratio = max(capacity, scale) / scale
        total = np.zeros_like(next(iter(items.values())))
        for item, cost in items.items():
            value = cost * ratio ** np.log2(1.0 - rates[item])
            if item in floors:
                value = np.maximum(value, floors[item])
            total += value
        return total
