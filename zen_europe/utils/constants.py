from dataclasses import dataclass


@dataclass(frozen=True)
class Constants:
    """
    Physical and unit-conversion constants used throughout the ZEN-europe
    project.

    Accessed directly on the class (e.g. ``Constants.HOURS_PER_YEAR``); no
    instantiation needed.
    """

    HOURS_PER_YEAR: float = 8760
    """Hours in a (non-leap) calendar year."""

    SECONDS_PER_HOUR: float = 3600

    HOURS_PER_DAY: float = 24

    HOURS_PER_WEEK: float = 168

    GJ_PER_MWH: float = 3.6
    """1 MWh = 3.6 GJ, from the definition 1 Wh = 3600 J."""

    TOE_PER_MWH: float = 0.0859845
    """IEA definition: 1 toe = 41.868 GJ = 11.63 MWh, so 1 MWh = 0.0859845 toe."""

    GJ_PER_KTOE: float = 1000 * GJ_PER_MWH / TOE_PER_MWH
    """1 ktoe = 1000 toe x 41.868 GJ/toe."""

    BARREL_PER_TON: float = 7.46
    """Conversion factor from tons of crude oil to barrels."""

    NATURAL_GAS_GWH_PER_BCM: float = 10600
    """Energy content of natural gas, GWh per billion cubic metre (bcm)."""

    LNG_GCV_KWH_PER_M3: float = 11.65
    """Gross calorific value of LNG, kWh per m3 (most common value in the SciGRID
    database)."""

    NATURAL_GAS_EJ_PER_BKG: float = 0.0381
    """Energy content of natural gas, EJ per billion kg.
    https://ocw.tudelft.nl/wp-content/uploads/Summary_table_with_heating_values_and_CO2_emissions.pdf
    """

    HYDROGEN_KWH_PER_KG: float = 33.3
    """lhv, https://www.nationalacademies.org/read/10922/chapter/21 """

    METHANOL_KWH_PER_KG: float = 5.54
    """ lhv, https://www.engineeringtoolbox.com/fuels-higher-calorific-values-d_169.html"""

    AMMONIA_GWH_PER_TON: float = 18.9 / 3600
    """ https://ens.dk/en/analyses-and-statistics/technology-data-renewable-fuels"""

    BIOCHAR_GWH_PER_TON: float = 25 / 3600
    """ https://ens.dk/en/analyses-and-statistics/technology-data-renewable-fuels"""

    DIESEL_KWH_PER_LITER: float = 36 / 3.6
    """lhv, from MJ/l to KWH/l, https://www.engineeringtoolbox.com/fuels-higher-calorific-values-d_169.html"""

    DENSITY_OIL: float = 800
    """kg/m3, p. 17 of
    https://static-content.springer.com/esm/art%3A10.1038%2Fs41558-021-01175-7/MediaObjects/41558_2021_1175_MOESM1_ESM.pdf
    """

    DENSITY_NATURAL_GAS: float = 150
    """kg/m3, under storage-reservoir conditions, p. 17 of
    https://static-content.springer.com/esm/art%3A10.1038%2Fs41558-021-01175-7/MediaObjects/41558_2021_1175_MOESM1_ESM.pdf
    """

    DENSITY_CO2: float = 700
    """kg/m3, supercritical CO2 under typical storage conditions, p. 17 of
    https://static-content.springer.com/esm/art%3A10.1038%2Fs41558-021-01175-7/MediaObjects/41558_2021_1175_MOESM1_ESM.pdf
    """

    DUIVEN_CAPTURE_CAPACITY: float = 0.1e6
    """tCO2/year captured by the Duiven plant, the size of a single
    first-of-a-kind carbon capture project."""
