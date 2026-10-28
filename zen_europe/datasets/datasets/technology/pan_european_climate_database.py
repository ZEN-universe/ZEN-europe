from __future__ import annotations

import logging
import urllib.request
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError

import cdsapi
import pandas as pd

if TYPE_CHECKING:
    from zen_creator import Element, Technology
    from zen_creator.utils.settings import Settings

from zen_creator import Attribute
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.utils.constants import Constants


class PanEuropeanClimateDatabase(Dataset[dict[str, pd.DataFrame]]):
    """
    Pan-European Climate Database (PECD 4.2) dataset class.

    Downloads hourly capacity factors for utility-scale solar PV, onshore wind, and
    offshore wind, plus hydropower generation and inflow energy, aggregated to NUTS0
    (country) resolution, from the Copernicus Climate Data Store's `sis-energy-pecd`
    dataset, for the historical ERA5-reanalysis `settings.time.time_series_year`.
    Wind technologies use PECD's "Existing technologies" turbine class (technology
    codes 20 offshore / 30 onshore) at the "Resource Grade B" installation-site
    assumption (current-plant-equivalent siting, as opposed to Grade A's idealized
    top-10%-of-locations siting); solar PV uses the utility-scale fixed-tilt panel
    technology (62); hydropower indicators have no technology/energy_scenario
    dimension in PECD.

    Solar PV is downloaded directly at NUTS0 resolution. Wind and hydropower are
    *not* available at NUTS0 -- PECD only reports them at its own regional zones
    (PEON/PEOF wind-farm-siting zones, SZON bidding zones), so this class downloads
    them at that native resolution and aggregates to NUTS0 itself, following
    ECMWF/ENTSO-E's own worked example:
    https://github.com/ecmwf-training/dss-notebooks/blob/main/datasets/sis-energy-pecd/aggregation-pecd-regions-into-nut0/aggregation-pecd-regions-into-nut0.ipynb

    - Wind (PEON/PEOF -> NUTS0): capacity-weighted average, using ECMWF/ENTSO-E's
      own pre-calculated per-region installed-capacity weight tables (downloaded
      from the same notebook's repo, see `_WIND_WEIGHT_SOURCES`) -- capacity factor
      is a ratio, so combining regions requires weighting by how much installed
      capacity each one actually represents, not a plain average. Offshore's weight
      table groups regions under a synthetic "{country}_OFF" pseudo-NUTS0 code
      (offshore areas aren't part of any real NUTS0 land region); the "_OFF" suffix
      is stripped to attribute offshore generation to the country whose exclusive
      economic zone the region sits in.
    - Hydropower (SZON -> NUTS0): no equivalent weight table exists for hydropower
      in the source notebook, so same-country SZON bidding zones are combined by a
      plain sum instead of a weighted average -- reservoir inflow is an absolute
      energy quantity, not a ratio, so summing same-country zones is the physically
      correct combination (unlike capacity factor, which needs weighting).
      SZON codes follow ENTSO-E's own convention of a leading 2-letter country
      prefix (e.g. "SE01"/"SE02"/"SE03"/"SE04" all belong to "SE"), which is enough
      to group them without a separate lookup table.

    Requires CDS API credentials configured in `~/.cdsapirc` (see
    https://cds.climate.copernicus.eu/how-to-api) -- this is a runtime download
    dependency, not a checked-in raw file, so nothing needs to be provided under
    `source_path` for this step to work; results (and the wind weight tables) are
    cached to `self.path` afterwards exactly like every other agency dataset in
    this package.
    """

    name = "pan_european_climate_database"

    CDS_DATASET = "sis-energy-pecd"
    # Pan-European bounding box [North, West, South, East], matching the CDS
    # dataset's own example request.
    AREA = [75, -31, 18, 45]

    # internal technology name -> CDS `variable`/`technology`/`energy_scenario`/
    # `spatial_resolution`. Wind and hydropower are downloaded at PECD's own native
    # regional resolution (not NUTS0) and aggregated to NUTS0 afterwards -- see
    # `_aggregate_to_nuts0`.
    TECHNOLOGY_REQUESTS: dict[str, dict[str, str | None]] = {
        "photovoltaics": {
            "variable": "solar_photovoltaic_generation_capacity_factor",
            "technology": "62",  # SPV utility-scale fixed
            "energy_scenario": None,
            "spatial_resolution": "nuts_0",
        },
        "wind_onshore": {
            "variable": "wind_power_onshore_capacity_factor",
            "technology": "30",  # onshore wind, existing technologies
            "energy_scenario": "resource_grade_b",
            "spatial_resolution": "peon",
        },
        "wind_offshore": {
            "variable": "wind_power_offshore_capacity_factor",
            "technology": "21",  # offshore wind, existing technologies
            "energy_scenario": "resource_grade_b",
            "spatial_resolution": "peof",
        },
        "reservoir_hydro": {
            "variable": "hydropower_reservoir_inflow",
            "technology": None,
            "energy_scenario": None,
            "spatial_resolution": "szon",
        },
        "run-of-river_hydro": {
            "variable": "hydropower_run_of_river_generation",
            "technology": None,
            "energy_scenario": None,
            "spatial_resolution": "szon",
        },
        "run-of-river_with_pondage_hydro": {
            "variable": "hydropower_run_of_river_with_pondage_generation",
            "technology": None,
            "energy_scenario": None,
            "spatial_resolution": "szon",
        },
        "pumped_hydro": {
            "variable": "hydropower_open_loop_pumped_storage_inflow",
            "technology": None,
            "energy_scenario": None,
            "spatial_resolution": "szon",
        },
    }

    # wind technology -> (cache filename, source URL) for ECMWF/ENTSO-E's own
    # pre-calculated PECD-region -> NUTS0 installed-capacity weight tables (the
    # "Existing_run.csv" variant, matching technology codes 20/30 = "Existing
    # technologies"; there's also a "Future_tech_runs.csv" variant in the same repo
    # for future-fleet technology codes, not used here).
    _WIND_WEIGHT_SOURCES: dict[str, tuple[str, str]] = {
        "wind_onshore": (
            "onshore_wind_weights.csv",
            "https://raw.githubusercontent.com/ecmwf-training/dss-notebooks/main/"
            "datasets/sis-energy-pecd/aggregation-pecd-regions-into-nut0/weights/"
            "PECD4.2/Onshore_Existing_run.csv",
        ),
        "wind_offshore": (
            "offshore_wind_weights.csv",
            "https://raw.githubusercontent.com/ecmwf-training/dss-notebooks/main/"
            "datasets/sis-energy-pecd/aggregation-pecd-regions-into-nut0/weights/"
            # "PECD4.2/Offshore_Existing_run.csv",
            # the "Existing" run has no data for countries without capacity in 2020
            # (e.g., IT)
            "PECD4.2/Offshore_Future_tech_runs.csv",
        ),
    }

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Climate and energy related variables from the Pan-European Climate "
                "Database derived from reanalysis and climate projections"
            ),
            author=["Copernicus"],
            publication="Copernicus",
            publication_year=2026,
            url="https://cds.climate.copernicus.eu/datasets/sis-energy-pecd?tab=overview",
            doi="https://doi.org/10.24381/cds.f323c5ec",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "climate_data"

    def _set_data(self) -> dict[str, pd.DataFrame]:
        year = self.settings.time.time_series_year
        return {
            technology: self._get_technology_data(technology, request, year)
            for technology, request in self.TECHNOLOGY_REQUESTS.items()
        }

    def _get_technology_data(
        self, technology: str, request: dict[str, str | None], year: int
    ) -> pd.DataFrame:
        """Return `technology`'s hourly NUTS0 series for `year`.

        Downloads and parses it from the CDS API on first use (aggregating from
        PECD's native regional resolution to NUTS0 where needed, see
        `_aggregate_to_nuts0`), caching the result as `pecd_data_<technology>.feather`
        directly under `self.path` (i.e. "separated by technology", one output
        file per technology); subsequent calls just read that cache back.
        """
        cache_path = self.path / f"pecd_data_{technology}.feather"
        if (
            cache_path.exists()
            and not self.settings.cache.overwrite_pan_european_climate_database
        ):
            return pd.read_feather(cache_path).set_index("Date")

        zip_path = self.path / f"{technology}_{year}_raw.zip"
        if (
            self.settings.cache.overwrite_pan_european_climate_database
            or not zip_path.exists()
        ):
            self._download(request, year, zip_path)

        data = self._parse_zip(zip_path)
        data = self._aggregate_to_nuts0(technology, data)
        data.reset_index().to_feather(cache_path)
        return data

    def _download(self, request: dict[str, str | None], year: int, dest: Path) -> None:
        """Retrieve one technology's PECD series from the CDS API as a raw zip file."""
        cds_request: dict[str, Any] = {
            "pecd_version": "pecd4_2",
            "temporal_period": ["historical"],
            "origin": ["era5_reanalysis"],
            "variable": [request["variable"]],
            "spatial_resolution": [request["spatial_resolution"]],
            "year": [str(year)],
            "file_version": ["fv1"],
            "area": self.AREA,
        }
        if request["technology"] is not None:
            cds_request["technology"] = [request["technology"]]
        if request["energy_scenario"] is not None:
            cds_request["energy_scenario"] = [request["energy_scenario"]]
        try:
            client = cdsapi.Client()
        except Exception as e:
            raise RuntimeError(
                "Failed to initialize CDS API client. Make sure you have a valid "
                "`~/.cdsapirc` file with your CDS API credentials. See "
                "https://cds.climate.copernicus.eu/how-to-api for instructions."
            ) from e
        try:
            logging.info(
                f"Downloading PECD data for {request['variable']} in {year}..."
            )
            client.retrieve(self.CDS_DATASET, cds_request, str(dest))
        except HTTPError as e:
            raise RuntimeError(
                f"Failed to download PECD data for {request['variable']} in {year}: {e}"
            ) from e

    @staticmethod
    def _parse_zip(zip_path: Path) -> pd.DataFrame:
        """Extract the single CSV the CDS API packages per request into a
        Date-indexed, PECD-region-columned hourly DataFrame."""
        with zipfile.ZipFile(zip_path) as archive:
            csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
            if len(csv_names) != 1:
                raise ValueError(
                    f"Expected exactly one CSV in '{zip_path.name}', found {csv_names}."
                )
            with archive.open(csv_names[0]) as csv_file:
                return pd.read_csv(
                    csv_file, comment="#", index_col=["Date"], parse_dates=["Date"]
                )

    def _aggregate_to_nuts0(self, technology: str, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate `data`'s PECD-region columns into NUTS0-country columns.

        `photovoltaics` is already downloaded at nuts_0 resolution and passes
        through unchanged; wind and hydro indicators are downloaded at PECD's
        own regional resolution (see `TECHNOLOGY_REQUESTS`) and need aggregating.
        """
        if technology == "photovoltaics":
            return data
        if technology in {
            "reservoir_hydro",
            "run-of-river_hydro",
            "run-of-river_with_pondage_hydro",
            "pumped_hydro",
        }:
            return self._aggregate_hydro_to_nuts0(data)
        return self._aggregate_wind_to_nuts0(technology, data)

    def _aggregate_wind_to_nuts0(
        self, technology: str, data: pd.DataFrame
    ) -> pd.DataFrame:
        """Capacity-weighted average of PEON/PEOF regional columns into NUTS0
        columns -- the same `Weight_in_aggregation`/sum/divide procedure as
        ECMWF/ENTSO-E's own aggregation notebook (see class docstring)."""
        weights = self._get_wind_weights(technology)
        weights = weights[weights["Weight_in_aggregation"] > 0]
        if technology == "wind_offshore":
            weights = weights.assign(NUTS0=weights["NUTS0"].str.removesuffix("_OFF"))

        region_to_country = weights.set_index("PECD_CODE")["NUTS0"]
        region_weight = weights.set_index("PECD_CODE")["Weight_in_aggregation"]

        missing = region_weight.index.difference(data.columns)
        if len(missing) > 0:
            logging.warning(
                f"{technology}: {len(missing)} weighted PECD region(s) not present "
                f"in the downloaded data, excluded from aggregation: {list(missing)}"
            )
            region_weight = region_weight.drop(missing)
            region_to_country = region_to_country.drop(missing)

        weighted = data[region_weight.index].multiply(region_weight, axis=1)
        aggregated = weighted.T.groupby(region_to_country).sum().T
        country_weight = region_weight.groupby(region_to_country).sum()
        return aggregated.divide(country_weight, axis=1)

    def _get_wind_weights(self, technology: str) -> pd.DataFrame:
        filename, url = self._WIND_WEIGHT_SOURCES[technology]
        weight_path = self.path / filename
        if (
            self.settings.cache.overwrite_pan_european_climate_database
            or not weight_path.exists()
        ):
            self._download_file(url, weight_path)
        return pd.read_csv(weight_path)

    # SZON bidding-zone codes follow ENTSO-E's own ISO-alpha2 country prefix (e.g.
    # "GR00" for Greece), which doesn't always match the NUTS0/model node code used
    # everywhere else in this package (e.g. `convert_country_names` maps Greece to
    # "EL", the Eurostat NUTS0 convention)
    _HYDRO_COUNTRY_CODE_FIXUPS: dict[str, str] = {"GR": "EL"}

    @classmethod
    def _aggregate_hydro_to_nuts0(cls, data: pd.DataFrame) -> pd.DataFrame:
        """Sum SZON bidding-zone columns sharing the same leading 2-letter country
        prefix into NUTS0-country columns (see class docstring for why summing,
        not weighting, is correct here)."""
        country = data.columns.str[:2].map(
            lambda code: cls._HYDRO_COUNTRY_CODE_FIXUPS.get(code, code)
        )
        return data.T.groupby(country).sum().T

    @staticmethod
    def _download_file(url: str, dest: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request) as response:
            dest.write_bytes(response.read())

    # -------- methods ------------------------

    def get_max_load(self, element: Technology) -> Attribute:
        """
        Get the maximum load (capacity factor) for a technology.

        Maximum load for solar and wind is taken from PECD capacity-factor data.
        Run-of-river maximum load is handled by HydropowerExistingCapacities,
        which can reconcile generation with the separate capacity dataset.

        Args:
            element: The element for which to get the maximum load.

        Returns:
            pd.Series: A pandas Series containing the maximum load data.
        """

        if element.name in ["photovoltaics", "wind_onshore", "wind_offshore"]:
            return self._get_max_load_solar_and_wind(element)
        raise ValueError(
            "Max load data is not available directly from the PECD dataset for "
            f"element {element.name}"
        )

    def _get_max_load_solar_and_wind(self, element: Technology) -> Attribute:
        """
        Get the maximum load for a technology.

        Args:
            element: The element for which to get the maximum load.

        Returns:
            pd.Series: A pandas Series containing the maximum load data.
        """
        assert element.name in self.data, (
            f"Maximum load data for {element.name} is not available in the "
            "PanEuropeanClimateDatabase dataset."
        )
        data = self.data[element.name]
        model_nodes = pd.Index(element.model.config.system.set_nodes)
        common_nodes = data.columns.intersection(model_nodes)
        missing_nodes = model_nodes.difference(common_nodes)
        if len(missing_nodes) > 0:
            logging.warning(
                f"No max load of {element.name} in PanEuropeanClimateDatabase data "
                "available for model nodes: "
                f"{missing_nodes}"
            )
        if data.min().min() < 0 and data.max().max() > 1:
            logging.info(
                f"PanEuropeanClimateDatabase data for {element.name} contains values "
                "outside the expected range [0, 1]:\n"
                f"min={data.min().min()}, max={data.max().max()}\n"
                "Clipping to [0, 1]."
            )
            data = data.clip(lower=0, upper=1)

        data = data[common_nodes]
        data = data.reset_index(drop=True)
        data.index.name = "time"
        source = SourceInformation(
            description=(
                f"The max load data for {element.name} is derived from the"
                "Pan-European Climate Database (PECD 4.2) dataset."
            ),
            metadata=self.metadata,
        )
        return element.max_load.set_data(
            source=source, df=data, unit="1", default_value=0
        )

    def get_generation_run_of_river_hydro(self, element: Element) -> pd.DataFrame:
        """
        Get combined run-of-river and pondage generation in GW.

        Args:
            element: An element providing the model nodes to retain.

        Returns:
            pd.DataFrame: Hourly run-of-river generation by model node.
        """
        # PECD's installed-capacity category is "Run-of-River and pondage".
        # Combine both generation indicators so the numerator uses exactly the
        # same technology boundary as the capacity denominator.
        data = self.data["run-of-river_hydro"].add(
            self.data["run-of-river_with_pondage_hydro"], fill_value=0
        )
        common_nodes = data.columns.intersection(element.model.config.system.set_nodes)
        missing_nodes = set(element.model.config.system.set_nodes).difference(
            common_nodes
        )
        if len(missing_nodes) > 0:
            logging.info(
                f"Missing nodes in PanEuropeanClimateDatabase data for {element.name}: "
                f"{missing_nodes}"
            )
        data = data[common_nodes]
        return self.convert_weekly_energy_to_hourly_flow(data)

    @staticmethod
    def convert_weekly_energy_to_hourly_flow(data: pd.DataFrame) -> pd.DataFrame:
        """Convert weekly energy in MWh to hourly flow in GW.

        Weekly energy is spread evenly across each week. PECD supplies 52 values,
        while the model uses 8,760 hours, so the final weekly rate is extended to
        cover the remaining 24 hours.
        """
        hours_per_week = int(Constants.HOURS_PER_WEEK)
        data = data.reset_index(drop=True)
        data.index = data.index * hours_per_week
        data = data.reindex(range(int(Constants.HOURS_PER_YEAR)), method="ffill")
        data = data / hours_per_week / 1000
        data.index.name = "time"
        return data
