from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.settings.cache import get_active_cache_settings

logger = logging.getLogger(__name__)

# Supplementary material of Cox et al. (2020), a copy of their "Input data.xlsx".
_INPUT_FILE = "input_data_cox_etal.xlsx"
_CACHE_FILE = "vehicle_tech_parameters.csv"
_PARAMETER_SHEET = "Car parameters"
_DRIVING_CYCLE_SHEET = "Driving cycles"

# Cox et al. run a Monte Carlo ensemble over triangular/uniform input
# distributions. Only the mode (the base value of every input) is used here,
# which makes the calculation deterministic and removes the sampling.
_BASE = "base"
# The input sheet holds a "current" (2017) and a "future" (2040) value for
# every parameter.
_TIMES = ["current", "future"]
# Cox et al. size vehicles for seven segments; the lower medium segment is the
# one representative car used in zen_europe.
_SIZE = "Lower medium"
_DRIVING_CYCLE = "WLTC"
_GROUP_ALL = "all"

# Powertrains of Cox et al. that are modelled here. FCEV is dropped, since
# there is no hydrogen passenger car in zen_europe; dropping it also removes
# every fuel-cell and hydrogen-tank parameter from the input.
_PETROL_CAR = "ICEV-p"
_DIESEL_CAR = "ICEV-d"
_GAS_CAR = "ICEV-g"
_HYBRID_CAR = "HEV-p"
_PHEV_COMBUSTION = "PHEV-c"
_PHEV_ELECTRIC = "PHEV-e"
_ELECTRIC_CAR = "BEV"
_PHEV = "PHEV"
_POWERTRAINS = [
    _PETROL_CAR,
    _DIESEL_CAR,
    _GAS_CAR,
    _HYBRID_CAR,
    _PHEV_COMBUSTION,
    _PHEV_ELECTRIC,
    _ELECTRIC_CAR,
]
# Combustion cars draw their auxiliary power as a mechanical load.
_COMBUSTION_ONLY = [_PETROL_CAR, _DIESEL_CAR, _GAS_CAR]
# Powertrains whose battery is sized by its energy content rather than by its
# power output.
_ENERGY_BATTERY = [_ELECTRIC_CAR, _PHEV_COMBUSTION, _PHEV_ELECTRIC]

# Names of the passenger car technologies in zen_europe.
_TECHNOLOGIES = {
    "BEV": _ELECTRIC_CAR,
    "ICE_diesel": _DIESEL_CAR,
    "ICE_petrol": _PETROL_CAR,
    "HEV": _HYBRID_CAR,
    "PHEV": _PHEV,
    "ICE_cng": _GAS_CAR,
}

# Masses that add up to the curb mass and the driving mass of a vehicle.
_CURB_MASS = [
    "glider base mass",
    "weight reduction",
    "engine mass",
    "emotor mass",
    "powertrain mass",
    "converter mass",
    "inverter mass",
    "charger mass",
    "power distribution unit mass",
    "battery cell mass",
    "battery BoP mass",
    "fuel tank mass",
    "CNG tank mass",
    "petrol mass",
    "diesel mass",
    "CNG mass",
]
_DRIVING_MASS = _CURB_MASS + ["total cargo mass"]
# The fuel masses carried on board, which size the fuel tank cost.
_FUEL_MASS = ["petrol mass", "diesel mass", "CNG mass"]

# Cost components that add up to the purchase price of a vehicle.
_PURCHASE_COST = [
    "glider cost",
    "lightweighting cost",
    "electric powertrain cost",
    "combustion powertrain cost",
    "power battery cost",
    "energy storage battery cost",
    "fuel tank cost",
    "heat pump cost",
    "battery onboard charging infrastructure cost",
    "combustion exhaust treatment cost",
]

# Quantities that the component sizing reads before it computes them, and that
# therefore have to exist on the first iteration.
_ITERATED = [
    "curb mass",
    "driving mass",
    "power",
    "engine power",
    "emotor power",
    "engine mass",
    "emotor mass",
    "powertrain mass",
    "power battery power",
    "battery cell mass",
    "battery BoP mass",
    "fuel tank mass",
    "CNG tank mass",
    "energy stored",
    "TtW energy",
    "electric utility factor",
]

# The mass iteration is converged once the driving mass moves by less than this
# many kg; Cox et al. give up after 50 iterations.
_MASS_TOLERANCE = 0.1
_MAX_ITERATIONS = 50

_AIR_DENSITY = 1.2  # kg/m3
_GRAVITY = 9.81  # m/s2
# Lower heating values used to convert a fuel mass into the energy stored.
_HEATING_VALUE = {"petrol mass": 42.4, "diesel mass": 48.0, "CNG mass": 55.5}  # MJ/kg
# Cox et al. fit the electric utility factor of a plug-in hybrid, i.e. the
# share of kilometres driven electrically, to the range data of Ploetz (2017).
_UTILITY_FACTOR_SLOPE = -0.01147
_UTILITY_FACTOR_EXPONENT = 1.186185

_HOURS_PER_YEAR = 8760
# TtW energy is given in kJ/vkm; 3.6e9 kJ make one GWh.
_KJ_PER_GWH = 3.6e9

_OUTPUT_COLUMNS = [
    "km per h",
    "lifetime",
    "capex",
    "capex_bat_cur",
    "capex_bat_fut",
    "vopex",
    "conversion_factor_electricity",
    "conversion_factor_fuel",
]
# The parameters that are monetary and therefore have to be rebased from the
# money year of Cox et al. to the configured price year.
_COST_COLUMNS = ["capex", "capex_bat_cur", "capex_bat_fut", "vopex"]

# The parameter that gives the demand of an input carrier per vehicle
# kilometre. Every fuel is covered by the same tank-to-wheel figure, since a
# car only ever burns one of them.
_CARRIER_PARAMETER = {
    "electricity": "conversion_factor_electricity",
    "gasoline": "conversion_factor_fuel",
    "diesel": "conversion_factor_fuel",
    "natural_gas": "conversion_factor_fuel",
}
# The energy demand and the maintenance cost are per vehicle kilometre.
_CONVERSION_FACTOR_UNIT = "GWh/vkm"
_OPEX_VARIABLE_UNIT = "Euro/vkm"


class PassengerCarsCox(Dataset[pd.DataFrame]):
    """Techno-economic parameters of passenger cars from Cox et al. (2020).

    Reimplements the vehicle model of Cox et al., reduced to what the
    zen_europe passenger car technologies need: the vehicle is sized over the
    WLTC driving cycle by iterating its mass, power and energy demand, and the
    resulting purchase price, maintenance cost and tank-to-wheel energy demand
    are scaled to the hourly vehicle mileage.

    Only the mode of the Monte Carlo ensemble of Cox et al. is evaluated, so
    the calculation is deterministic.
    """

    name = "passenger_cars_cox"

    # the money year is not explicitly stated, so we assume it is the
    # publication year of the paper
    MONEY_YEAR = 2020

    def __init__(self, source_path: Path | str | None = None):
        # only read when the parameters are not already cached on disk
        self._driving_cycle: np.ndarray | None = None
        super().__init__(source_path=source_path)
        self.get_inflation_rate = ECBInflation().get_inflation_rate

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Life cycle environmental and cost comparison of current and "
                "future passenger cars under different energy scenarios"
            ),
            author=[
                "Brian Cox",
                "Christian Bauer",
                "Angelica Mendoza Beltran",
                "Detlef P. van Vuuren",
                "Christopher L. Mutel",
            ],
            publication="Applied Energy",
            publication_year=2020,
            url=("https://www.sciencedirect.com/science/article/pii/S030626192030533X"),
            doi="10.1016/j.apenergy.2020.115021",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "passenger_cars"

    def _set_data(self) -> pd.DataFrame:
        return self._cached_parameters()

    # -------- disk cache ------------------

    def _cached_parameters(self) -> pd.DataFrame:
        """Return the calculated vehicle parameters, computing and caching them
        on first use."""
        cache_path = self.path / _CACHE_FILE
        overwrite = get_active_cache_settings().overwrite_passenger_cars_cox
        if cache_path.exists() and not overwrite:
            cached = pd.read_csv(cache_path, index_col="tech")
            # a cache written before a parameter was added is stale
            if list(cached.columns) == _OUTPUT_COLUMNS:
                logger.info(
                    f"Loading cached passenger car parameters from {cache_path}"
                )
                return cached
            logger.info(
                f"The cached passenger car parameters in {cache_path} are "
                "outdated and are recalculated."
            )

        logger.info("Calculating passenger car parameters from Cox et al. (2020)...")
        parameters = self._calculate_parameters()
        parameters.to_csv(cache_path)
        return parameters

    # -------- raw input ------------------

    def _read_base_values(self) -> dict[str, dict[str, dict[str, dict[str, float]]]]:
        """Read the mode of every vehicle parameter from the input sheet.

        Returns:
            The base values, keyed by time, parameter, powertrain group and
            size group. Both groups list the vehicles they apply to, e.g.
            'BEV, PHEV-e' or 'all'.
        """
        data = pd.read_excel(
            self.path / _INPUT_FILE,
            sheet_name=_PARAMETER_SHEET,
            header=[0, 1],
            index_col=[0, 1, 2, 3, 4],
        )
        # drop the category (e.g. 'Glider') and order the index as
        # parameter / powertrain group / size group / distribution
        data = data.reset_index(level=[0], drop=True)
        data = data.reorder_levels([2, 0, 1, 3]).sort_index()

        base_values: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
        for time in _TIMES:
            base_values[time] = {}
            for key, value in data[(time, _BASE)].items():
                parameter, powertrain, size, _ = cast(tuple[str, str, str, Any], key)
                # a parameter is reported once per distribution, and every
                # distribution shares the same mode
                base_values[time].setdefault(parameter, {}).setdefault(
                    powertrain, {}
                ).setdefault(size, value)
        return base_values

    def _read_driving_cycle(self) -> np.ndarray:
        """Read the speed profile of the WLTC driving cycle in km/h."""
        cycle = pd.read_excel(self.path / _INPUT_FILE, sheet_name=_DRIVING_CYCLE_SHEET)
        return cycle.set_index("Time (s)")[_DRIVING_CYCLE].dropna().to_numpy()

    def _build_cars(self) -> pd.DataFrame:
        """Assign the input parameters to every time and powertrain.

        A parameter is reported for a group of powertrains and a group of
        sizes, so the group that contains the vehicle at hand is looked up for
        each of the two. Parameters that do not apply to a powertrain are left
        missing.
        """
        base_values = self._read_base_values()
        cars: dict[tuple[str, str], dict[str, float]] = {}
        for time in _TIMES:
            for powertrain in _POWERTRAINS:
                car: dict[str, float] = {}
                for parameter, groups in base_values[time].items():
                    powertrain_group = self._find_group(groups, powertrain)
                    if powertrain_group is None:
                        continue
                    size_group = self._find_group(groups[powertrain_group], _SIZE)
                    if size_group is None:
                        raise ValueError(
                            f"No size group of '{parameter}' covers '{_SIZE}'."
                        )
                    car[parameter] = groups[powertrain_group][size_group]
                cars[(time, powertrain)] = car

        data = pd.DataFrame.from_dict(cars, orient="index")
        data.index = pd.MultiIndex.from_tuples(data.index, names=["time", "powertrain"])
        data["powertrain"] = data.index.get_level_values("powertrain")
        return data

    @staticmethod
    def _find_group(groups: dict[str, Any], member: str) -> str | None:
        """Return the group of vehicles that covers `member`, or None if the
        parameter does not apply to it."""
        if _GROUP_ALL in groups:
            return _GROUP_ALL
        matches = [group for group in groups if member in group]
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"'{member}' is covered by more than one group: {matches}."
            )
        return matches[0]

    # -------- vehicle model ------------------

    def _set_derived_parameters(self, cars: pd.DataFrame) -> pd.DataFrame:
        """Derive the vehicle parameters that follow directly from the input."""
        cars["weight reduction"] = (
            -1 * cars["glider base mass"] * cars["lightweighting"]
        )
        cars["total cargo mass"] = (
            cars["average passengers"] * cars["average passenger mass"]
            + cars["cargo mass"]
        )
        cars["auxiliary power demand"] = (
            cars["auxilliary power base demand"]
            + cars["heating thermal demand"] * cars["heating energy consumption"]
            + cars["cooling thermal demand"] * cars["cooling energy consumption"]
        )
        cars["TtW efficiency"] = (
            cars["battery discharge efficiency"].fillna(1)
            * cars["drivetrain efficiency"].fillna(1)
            * cars["engine efficiency"].fillna(1)
        )
        cars["recuperation efficiency"] = (
            cars["drivetrain efficiency"] * cars["battery charge efficiency"]
        )
        for parameter in _ITERATED:
            cars[parameter] = np.nan
        return cars

    @staticmethod
    def _sum_mass(car: dict) -> dict:
        """Sum the component masses into the curb mass and the driving mass.

        A component that a powertrain does not have is missing rather than
        zero, hence the nansum.
        """
        car["curb mass"] = np.nansum([car.get(mass, np.nan) for mass in _CURB_MASS])
        car["driving mass"] = np.nansum(
            [car.get(mass, np.nan) for mass in _DRIVING_MASS]
        )
        return car

    @staticmethod
    def _size_components(car: dict) -> dict:
        """Size the powertrain, the battery and the fuel tank of one vehicle
        from its curb mass."""
        powertrain = car["powertrain"]

        car["power"] = car["power to mass ratio"] * car["curb mass"] / 1000
        car["engine power"] = car["power"] * car["combustion power share"]
        if powertrain in _ENERGY_BATTERY:
            car["emotor power"] = car["power"]
        else:
            car["emotor power"] = car["power"] * (1 - car["combustion power share"])

        car["engine mass"] = (
            car["engine power"] * car["engine mass per power"]
            + car["engine fixed mass"]
        )
        car["emotor mass"] = (
            car["emotor power"] * car["emotor mass per power"]
            + car["emotor fixed mass"]
        )
        car["powertrain mass"] = (
            car["power"] * car["powertrain mass per power"]
            + car["powertrain fixed mass"]
        )

        if powertrain in _ENERGY_BATTERY:
            # the battery is sized by the energy it stores
            car["battery cell mass"] = (
                car["energy battery mass"] * car["battery cell mass share"]
            )
            car["battery BoP mass"] = car["energy battery mass"] * (
                1 - car["battery cell mass share"]
            )
        else:
            # the battery only has to deliver the power of the electric motor
            car["power battery power"] = car["emotor power"]
            car["battery cell mass"] = (
                car["power battery power"] / car["battery cell power density"]
            )
            car["battery BoP mass"] = car["battery cell mass"] * (
                1 - car["battery cell mass share"]
            )

        # energy contained in the fuel carried on board, in kWh
        if powertrain == _GAS_CAR:
            fuel_energy = car["CNG mass"] * _HEATING_VALUE["CNG mass"] / 3.6
        elif powertrain == _DIESEL_CAR:
            fuel_energy = car["diesel mass"] * _HEATING_VALUE["diesel mass"] / 3.6
        elif powertrain != _ELECTRIC_CAR:
            fuel_energy = car["petrol mass"] * _HEATING_VALUE["petrol mass"] / 3.6
        else:
            fuel_energy = 0.0

        # the cars that run on their battery store their energy in it, every
        # other car in its fuel
        if powertrain in [_ELECTRIC_CAR, _PHEV_ELECTRIC]:
            car["energy stored"] = (
                car["battery cell mass"] * car["battery cell energy density"]
            )  # kWh
        else:
            car["energy stored"] = fuel_energy

        if powertrain == _GAS_CAR:
            car["CNG tank mass"] = (
                fuel_energy * car["CNG tank mass slope"]
                + car["CNG tank mass intercept"]
            )
        elif powertrain != _ELECTRIC_CAR:
            car["fuel tank mass"] = fuel_energy * car["fuel tank mass per energy"]
        return car

    def _tank_to_wheel_energy(self, car: dict) -> float:
        """Tank-to-wheel energy demand of one vehicle over the driving cycle.

        Returns:
            The energy demand in kJ/vkm.
        """
        cycle = self._driving_cycle
        assert cycle is not None, "The driving cycle has not been read yet."
        velocity = cycle / 3.6  # km/h to m/s

        acceleration = np.zeros(cycle.shape)
        acceleration[1:-1] = (velocity[2:] - velocity[:-2]) / 2

        kinetic_force = acceleration * car["driving mass"]
        rolling_resistance = (
            car["driving mass"] * car["rolling resistance coefficient"] * _GRAVITY
        )
        air_resistance = (
            velocity**2
            * car["frontal area"]
            * car["aerodynamic drag coefficient"]
            * _AIR_DENSITY
            / 2
        )

        # Total force at the wheel. Rolling and air resistance always resist
        # the motion, the kinetic force is negative while the car decelerates.
        total_force = kinetic_force + rolling_resistance + air_resistance
        power = total_force * velocity
        decelerating = total_force < 0

        # The powertrain recuperates the braking power that does not exceed the
        # power of the electric motor, within the efficiency limits.
        braking_power = np.where(decelerating, power, 0.0)
        recuperated_power = (
            np.clip(braking_power, -1000 * car["emotor power"], None)
            * car["recuperation efficiency"]
        )
        traction_power = np.where(decelerating, 0.0, power)

        distance = velocity.sum() / 1000  # m/s over 1 s steps, in km
        auxiliary_energy = (
            car["auxiliary power demand"] * cycle.size / distance / 1000
        )  # kJ/km
        if car["powertrain"] in _COMBUSTION_ONLY:
            # the auxiliaries of a combustion car are a mechanical load
            auxiliary_energy = auxiliary_energy / car["engine efficiency"]

        return (traction_power.sum() + recuperated_power.sum()) / (
            1000 * distance
        ) / car["TtW efficiency"] + auxiliary_energy

    @staticmethod
    def _calculate_costs(car: dict) -> dict:
        """Calculate the purchase price and the maintenance cost of one
        vehicle."""
        car["glider cost"] = (
            car["glider base mass"] * car["glider cost slope"]
            + car["glider cost intercept"]
        ) * car["markup factor"]
        car["lightweighting cost"] = (
            -1
            * car["weight reduction"]
            * car["glider lightweighting cost per kg"]
            * car["markup factor"]
        )
        car["electric powertrain cost"] = (
            car["electric powertrain cost per kW"]
            * car["emotor power"]
            * car["markup factor"]
        )
        car["combustion powertrain cost"] = (
            car["engine power"]
            * car["combustion powertrain cost per kW"]
            * car["markup factor"]
        )
        car["power battery cost"] = (
            car["power battery power"]
            * car["power battery cost per kW"]
            * car["markup factor"]
        )
        car["energy storage battery cost"] = (
            car["energy storage battery cost per kWh"]
            * car["battery cell mass"]
            * car["battery cell energy density"]
            * car["markup factor"]
        )

        if car["powertrain"] == _ELECTRIC_CAR:
            car["fuel tank cost"] = 0
        else:
            car["fuel tank cost"] = (
                car["fuel tank cost per kg"]
                * np.nansum([car[fuel] for fuel in _FUEL_MASS])
                * car["markup factor"]
            )

        car["purchase cost"] = np.nansum([car[cost] for cost in _PURCHASE_COST])
        car["maintenance cost"] = (
            car["maintenance cost per glider cost"]
            * car["glider cost"]
            / car["kilometers per year"]
        )
        return car

    def _iterate_mass_and_energy(self, cars: pd.DataFrame) -> pd.DataFrame:
        """Size every vehicle by iterating its mass, power and energy demand.

        The component masses depend on the power of the vehicle, which in turn
        depends on its mass, so mass and energy demand are iterated until the
        driving mass no longer changes.
        """
        # a dict of dicts is considerably faster to iterate over than a frame
        fleet = cars.to_dict(orient="index")

        for index, car in fleet.items():
            car = self._sum_mass(self._size_components(car))
            old_mass = 0.0
            iteration = 0
            while abs(old_mass - car["driving mass"]) > _MASS_TOLERANCE:
                old_mass = car["driving mass"]
                car["TtW energy"] = self._tank_to_wheel_energy(car)
                car = self._sum_mass(self._size_components(self._sum_mass(car)))
                iteration += 1
                if iteration == _MAX_ITERATIONS:
                    raise RuntimeError(
                        f"The mass of the vehicle {index} did not converge "
                        f"within {_MAX_ITERATIONS} iterations."
                    )
            if car["TtW energy"] < 0:
                raise ValueError(f"The vehicle {index} has a negative energy demand.")
            fleet[index] = self._calculate_costs(car)

        cars = pd.DataFrame.from_dict(fleet, orient="index")
        cars.index = pd.MultiIndex.from_tuples(cars.index, names=["time", "powertrain"])
        cars["range"] = (
            cars["energy stored"]
            * 3600
            * cars["battery DoD"].fillna(1)
            / cars["TtW energy"]
        )
        # share of the kilometres a plug-in hybrid drives electrically
        cars["electric utility factor"] = np.where(
            cars["powertrain"] == _PHEV_ELECTRIC,
            (1 - np.exp(_UTILITY_FACTOR_SLOPE * cars["range"]))
            ** _UTILITY_FACTOR_EXPONENT,
            cars["electric utility factor"],
        )
        return cars

    @staticmethod
    def _add_average_phev(cars: pd.DataFrame) -> pd.DataFrame:
        """Average the electric and the combustion mode of the plug-in hybrid
        into a single vehicle, weighted by the electric utility factor."""
        cars = cars.swaplevel().sort_index()
        electric = cars.loc[_PHEV_ELECTRIC]
        combustion = cars.loc[_PHEV_COMBUSTION]
        utility_factor = electric["electric utility factor"]

        phev = electric.copy()
        for column in phev.columns:
            if column == "powertrain":
                phev[column] = _PHEV
            if phev[column].dtype not in ["float64", "int64"]:
                continue
            if column == "electric utility factor":
                continue
            if electric[column].isnull().all() and combustion[column].isnull().all():
                continue
            if column in ["range", "energy stored"]:
                phev[column] = electric[column] + combustion[column]
            elif column in ["battery discharge efficiency", "battery DoD"]:
                phev[column] = electric[column]
            else:
                phev[column] = electric[column].fillna(0) * utility_factor + combustion[
                    column
                ].fillna(0) * (1 - utility_factor)

        phev = pd.concat({_PHEV: phev}, names=["powertrain", "time"])
        return pd.concat([cars, phev]).swaplevel().sort_index()

    # -------- parameters ------------------

    def _calculate_parameters(self) -> pd.DataFrame:
        """Size the vehicles and scale their costs and energy demand to the
        hourly vehicle mileage.

        Returns:
            The parameters indexed by the zen_europe technology name.
        """
        self._driving_cycle = self._read_driving_cycle()
        cars = self._set_derived_parameters(self._build_cars())
        cars = self._add_average_phev(self._iterate_mass_and_energy(cars))

        current = cast(pd.DataFrame, cars.loc["current"])
        parameters = pd.DataFrame(index=list(_TECHNOLOGIES), columns=_OUTPUT_COLUMNS)
        parameters.index.name = "tech"
        for technology, powertrain in _TECHNOLOGIES.items():
            car = cast(pd.Series, current.loc[powertrain])
            markup = car["markup factor"]
            # the capacity of a vehicle is its hourly mileage
            mileage = car["kilometers per year"] / _HOURS_PER_YEAR
            # the cost components are reported at the consumer price, whereas
            # zen_europe uses the manufacturing cost
            parameters.loc[technology, "km per h"] = mileage
            # the years a car lasts before its lifetime mileage is driven
            parameters.loc[technology, "lifetime"] = round(
                car["lifetime kilometers"] / car["kilometers per year"]
            )
            parameters.loc[technology, "capex"] = (
                car["purchase cost"] / mileage / markup
            )
            parameters.loc[technology, "capex_bat_cur"] = (
                car["energy storage battery cost"] / mileage / markup
            )
            parameters.loc[technology, "capex_bat_fut"] = (
                cast(
                    float,
                    cars.loc[("future", powertrain), "energy storage battery cost"],
                )
                / mileage
                / markup
            )
            parameters.loc[technology, "vopex"] = car["maintenance cost"] / markup
            parameters.loc[technology, "conversion_factor_electricity"] = (
                self._electricity_demand(car) / _KJ_PER_GWH
            )
            parameters.loc[technology, "conversion_factor_fuel"] = (
                self._fuel_demand(car) / _KJ_PER_GWH
            )
        return parameters.astype(float)

    @staticmethod
    def _electricity_demand(car: pd.Series) -> float:
        """Electricity drawn from the grid per vehicle kilometre, in kJ/vkm.

        The tank-to-wheel energy is the energy at the wheel, so it is converted
        back to the energy taken from the grid via the drivetrain and charging
        efficiencies. Cars without a plug do not draw any electricity.
        """
        if car["powertrain"] not in [_ELECTRIC_CAR, _PHEV]:
            return np.nan
        electric_share = (
            1 if car["powertrain"] == _ELECTRIC_CAR else car["electric utility factor"]
        )
        return (
            car["TtW energy"]
            * electric_share
            * car["battery charge efficiency"]
            / car["TtW efficiency"]
        )

    @staticmethod
    def _fuel_demand(car: pd.Series) -> float:
        """Fuel burnt per vehicle kilometre, in kJ/vkm.

        The tank-to-wheel energy of a combustion car already is the energy in
        the fuel. A battery electric car does not burn any fuel.
        """
        if car["powertrain"] == _ELECTRIC_CAR:
            return np.nan
        if car["powertrain"] == _PHEV:
            return car["TtW energy"] * (1 - car["electric utility factor"])
        return car["TtW energy"]

    # -------- outward-facing accessors ------------------

    def get_parameters(self) -> pd.DataFrame:
        """All calculated parameters, indexed by the zen_europe technology
        name."""
        return self.data

    def get_parameter(self, technology: str, parameter: str) -> float:
        """One calculated parameter of one passenger car technology.

        Args:
            technology: Name of the technology in zen_europe, e.g. 'BEV'.
            parameter: Name of the parameter, e.g. 'capex'.

        Returns:
            The value of the parameter.
        """
        if technology not in self.data.index:
            raise ValueError(
                f"Cox et al. (2020) does not cover the technology "
                f"'{technology}', expected one of {sorted(_TECHNOLOGIES)}."
            )
        if parameter not in self.data.columns:
            raise ValueError(
                f"Unknown parameter '{parameter}', expected one of "
                f"{_OUTPUT_COLUMNS}."
            )
        return cast(float, self.data.loc[technology, parameter])

    def get_cost(self, element: ConversionTechnology, parameter: str) -> float:
        """Return one passenger-car cost rebased to the configured price year.

        Args:
            element: The passenger car for which to get the cost.
            parameter: Name of the cost parameter, e.g. 'capex'.

        Returns:
            The cost in Euro of the configured price year.
        """
        if parameter not in _COST_COLUMNS:
            raise ValueError(
                f"'{parameter}' is not a cost parameter, expected one of "
                f"{_COST_COLUMNS}."
            )
        inflation = self.get_inflation_rate(
            base_year=self.MONEY_YEAR, target_year=element.settings.time.price_year
        )
        return float(self.get_parameter(element.name, parameter)) * inflation

    # -------- attribute setters ------------------

    def get_lifetime(self, element: ConversionTechnology) -> Attribute:
        """Get the lifetime of the specified passenger car.

        Args:
            element: The passenger car for which to get the lifetime.

        Returns:
            Attribute: The lifetime of the car in years.
        """
        attr = element.lifetime
        return attr.set_data(
            default_value=int(self.get_parameter(element.name, "lifetime")),
            source=SourceInformation(
                description=(
                    f"The lifetime of {element.name} is obtained by dividing "
                    "the lifetime mileage of the lower medium car of Cox et "
                    "al. (2020) by its annual mileage, rounded to full years."
                ),
                metadata=self.metadata,
            ),
            unit="1",
        )

    def get_conversion_factor(self, element: ConversionTechnology) -> Attribute:
        """Get the conversion factor of the specified passenger car.

        Args:
            element: The passenger car for which to get the conversion factor.

        Returns:
            Attribute: The energy demand of every input carrier of the car per
            vehicle kilometre driven.
        """
        conversion_factors = []
        for carrier in cast(list[str], element.input_carrier.default_value):
            if carrier not in _CARRIER_PARAMETER:
                raise ValueError(
                    f"Cox et al. (2020) does not report the demand of "
                    f"'{carrier}' for '{element.name}'."
                )
            value = self.get_parameter(element.name, _CARRIER_PARAMETER[carrier])
            if pd.isna(value):
                raise ValueError(
                    f"Cox et al. (2020) reports no '{carrier}' demand for "
                    f"'{element.name}'."
                )
            conversion_factors.append(
                {
                    carrier: {
                        "default_value": float(value),
                        "unit": _CONVERSION_FACTOR_UNIT,
                    }
                }
            )

        attr = element.conversion_factor
        return attr.set_data(
            default_value=conversion_factors,
            source=SourceInformation(
                description=(
                    f"The conversion factor of {element.name} is the "
                    "tank-to-wheel energy demand of the lower medium car of "
                    "Cox et al. (2020) over the WLTC driving cycle. For a "
                    "battery electric car it is the electricity drawn from "
                    "the grid, so it includes the charging and drivetrain "
                    "losses."
                ),
                metadata=self.metadata,
            ),
        )

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """Get the specific variable OPEX of the specified passenger car.

        Args:
            element: The passenger car for which to get the specific variable
                OPEX.

        Returns:
            Attribute: The maintenance cost of the car per vehicle kilometre.
        """
        attr = element.opex_specific_variable
        return attr.set_data(
            default_value=self.get_cost(element, "vopex"),
            source=SourceInformation(
                description=(
                    f"The specific variable OPEX of {element.name} is the "
                    "maintenance cost of the lower medium car of Cox et al. "
                    "(2020), taken at the manufacturing cost rather than at "
                    "the consumer price, i.e. divided by the markup factor. "
                    f"Monetary values are rebased from {self.MONEY_YEAR} to "
                    f"{element.settings.time.price_year} Euro using ECB "
                    "HICP inflation."
                ),
                metadata=self.metadata,
            ),
            unit=_OPEX_VARIABLE_UNIT,
        )
