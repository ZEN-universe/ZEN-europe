from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.utils.utils import format_capacity_existing


class EuropeanBiogasAssociation(Dataset[pd.DataFrame]):
    """
    European Biogas Association dataset class for existing biomethane conversion
    capacity.

    The 2020 edition of the EBA-GIE biomethane map lists a capacity for every single
    plant, so capacity additions up to 2020 are taken straight from it. The 2026 edition
    no longer reports capacities, only plant counts, so the additions from the 2020 map
    date to mid-2026 are modelled: the plant counts are read off the 2026 map, allocated
    to years with the European yearly profile printed on that map, and valued with an
    average capacity per plant. See get_capacity_existing for the full chain.

    """

    name = "european_biogas_association"

    DEFAULT_LHV_BIOMETHANE = 10  # kWh/m3, https://www.iea.org/reports/outlook-for-biogas-and-biomethane-prospects-for-organic-growth/an-introduction-to-biogas-and-biomethane

    # ---------------------------------------------------------------- 2026 map
    # Everything below is read off the European Biomethane Map 2026 (version June 2026),
    # file GIE_EBA_BIO_2026_A0_FULL_115.pdf. The map itself is not parsed at runtime
    # because it is a single A0 poster with no tabular data layer.

    # Country circles: the number above the dividing line (total installed plants) and
    # the number below it (newly installed plants, drawn in orange). Cross-checked by
    # classifying the colour of the box behind all 1978 facility labels on the map;
    # the two readings agree everywhere except BE (18 labels / 3 orange) and DE (29
    # orange), where the printed circle values below are used.
    PLANTS_TOTAL_2026 = {
        "AT": 20,
        "BE": 17,
        "CH": 48,
        "CZ": 13,
        "DE": 285,
        "DK": 61,
        "EE": 12,
        "ES": 26,
        "FI": 32,
        "FR": 829,
        "HU": 2,
        "IE": 2,
        "IS": 2,
        "IT": 273,
        "LI": 1,
        "LT": 12,
        "LU": 2,
        "LV": 12,
        "NL": 92,
        "NO": 15,
        "PL": 1,
        "PT": 13,
        "SE": 67,
        "SK": 5,
        "UA": 7,
        "UK": 128,
    }
    PLANTS_NEW_2026 = {
        "AT": 6,
        "BE": 2,
        "CH": 5,
        "CZ": 0,
        "DE": 28,
        "DK": 3,
        "EE": 4,
        "ES": 11,
        "FI": 3,
        "FR": 87,
        "HU": 0,
        "IE": 0,
        "IS": 0,
        "IT": 136,
        "LI": 0,
        "LT": 7,
        "LU": 0,
        "LV": 4,
        "NL": 5,
        "NO": 0,
        "PL": 0,
        "PT": 8,
        "SE": 4,
        "SK": 3,
        "UA": 0,
        "UK": 9,
    }

    # "Evolution of European biomethane production facilities" chart on the same map.
    # Each bar is the number of plants standing at the start of the year (dark) plus the
    # plants commissioned during it (light).
    EU_PLANTS_EXISTING = {
        2011: 182,
        2012: 182,
        2013: 243,
        2014: 302,
        2015: 373,
        2016: 431,
        2017: 504,
        2018: 562,
        2019: 627,
        2020: 718,
        2021: 884,
        2022: 1064,
        2023: 1306,
        2024: 1509,
        2025: 1620,
    }
    EU_PLANTS_NEW = {
        2012: 61,
        2013: 59,
        2014: 71,
        2015: 58,
        2016: 73,
        2017: 58,
        2018: 65,
        2019: 91,
        2020: 166,
        2021: 180,
        2022: 242,
        2023: 204,
        2024: 111,
        2025: 267,
    }

    # EBA press figures for the 2026 edition, used to size the plants the map does not
    # give a capacity for.
    # https://www.bioenergy-news.com/news/europes-biomethane-capacity-passes-8-bcm-as-investment-commitments-reach-e36-billion/
    EU_PLANTS_TOTAL_2026 = 1975  # plants in operation, Q2 2026
    EU_AVG_CAPACITY_2026 = 472.0  # Nm3/h, European average plant size
    AVG_CAPACITY_2026 = {"DK": 1528.0, "FR": 212.0, "IT": 667.0, "DE": 607.0}

    # The orange plants on the 2026 map are the ones added since the previous edition,
    # whose data are from Q1 2025 - not a calendar year. 1977 - 325 = 1652 against the
    # 1678 plants that edition reported, which is what pins the window down.
    # https://ceenergynews.com/bioenergy/gie-and-eba-release-2025-european-biomethane-map/
    PLANTS_ADDED_Q1_2025 = 46
    YEAR_LAST = 2026  # the 2026 map is a June 2026 snapshot, so this year is H1 only

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("EBA-GiE biomethane map 2020 and 2026"),
            author=["European Biogas Association (EBA)"],
            publication="EBA-GiE biomethane map",
            publication_year=2026,
            url="https://www.europeanbiogas.eu/publication/european-biomethane-map-2026/",
            note=(
                "Per-plant capacities and commissioning years are from the 2020 "
                "edition "
                "(https://www.europeanbiogas.eu/publication/eba-gie-biomethane-map-2020/)."
                " The 2026 edition reports plant counts only and is entered as "
                "constants on the dataset class."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "03-technology"
            / "capacity_existing"
            / "biomethane_conversion"
        )

    def _set_data(self) -> dict[str, pd.Series]:
        data = pd.read_excel(
            self.path / "biomethane_production.xlsx", sheet_name="Append1"
        )
        return data

    # -------- 2020 map -----------------------
    def get_plants_2020(self) -> pd.DataFrame:
        """
        One row per plant on the 2020 map.

        The sheet interleaves country headers with plant rows, so rows are kept only if
        the first column looks like a facility label ("AT-1"). Capacity and year are "-"
        where the map reports nothing; both become NaN here.

        Returns:
            pd.DataFrame: columns node, plant_id, capacity_existing, year_construction.
        """
        rename_cols = {
            "Column1": "plant_id",
            "Column6": "capacity_existing",
            "Column9": "year_construction",
        }
        plants = self.data.rename(rename_cols, axis=1)
        is_plant = plants["plant_id"].astype(str).str.match(r"^[A-Z]{2}-\d+$", na=False)
        plants = plants.loc[is_plant, list(rename_cols.values())].copy()
        plants["node"] = plants["plant_id"].str.split("-", expand=True)[0]
        for col in ["capacity_existing", "year_construction"]:
            plants[col] = pd.to_numeric(plants[col], errors="coerce")
        return plants[["node", "plant_id", "capacity_existing", "year_construction"]]

    def get_capacity_existing_2020(self) -> pd.Series:
        """
        Capacity commissioned per node and year as recorded on the 2020 map [Nm3/h].

        Plants with no reported capacity are dropped, as they carry no capacity to
        allocate. Plants with no reported year are assigned the median commissioning
        year of the plants that do report one.

        Returns:
            pd.Series: indexed by node and year_construction.
        """
        plants = self.get_plants_2020()
        plants = plants[plants["capacity_existing"].notna()].copy()
        median_year = int(np.median(plants["year_construction"].dropna()))
        plants["year_construction"] = (
            plants["year_construction"].fillna(median_year).astype(int)
        )
        return plants.groupby(["node", "year_construction"])["capacity_existing"].sum()

    def get_plant_count_2020(self) -> pd.Series:
        """
        Plants per node on the 2020 map, including those with no reported capacity.

        This is the count the 2026 plant counts are differenced against, so it has to be
        the full 729 plants rather than the 672 that report a capacity.

        Returns:
            pd.Series: indexed by node.
        """
        return self.get_plants_2020().groupby("node")["plant_id"].count()

    # -------- capacity per plant -------------
    def get_average_capacity_2026(self) -> tuple[pd.Series, float]:
        """
        Average capacity per plant applied to plants built after the 2020 map [Nm3/h].

        Denmark, France, Italy and Germany take the average EBA published for the 2026
        map. Every other node takes its own 2020-map average scaled by a single factor,
        chosen so the modelled 2026 fleet comes to the 8.2 bcm/yr EBA reports; nodes
        absent from the 2020 map start from the 2020 European average instead.

        Returns:
            tuple: the average capacity per node, and the calibration factor.
        """
        plants_2020 = self.get_plants_2020()
        plants_2020 = plants_2020[plants_2020["capacity_existing"].notna()]
        average_2020 = plants_2020.groupby("node")["capacity_existing"].mean()
        average_2020_eu = plants_2020["capacity_existing"].mean()

        nodes = sorted(self.PLANTS_TOTAL_2026)
        plants_2026 = pd.Series(self.PLANTS_TOTAL_2026).reindex(nodes)
        published = pd.Series(self.AVG_CAPACITY_2026).reindex(nodes)
        base = average_2020.reindex(nodes).fillna(average_2020_eu)

        is_published = published.notna()
        target = self.EU_PLANTS_TOTAL_2026 * self.EU_AVG_CAPACITY_2026
        calibration_factor = (
            target - (plants_2026[is_published] * published[is_published]).sum()
        ) / (plants_2026[~is_published] * base[~is_published]).sum()

        average_2026 = base * calibration_factor
        average_2026[is_published] = published[is_published]
        return average_2026, calibration_factor

    # -------- 2026 map -----------------------
    def get_year_weights(self) -> tuple[pd.Series, pd.Series]:
        """
        European plant additions per year, split into the two windows the 2026 map
        spans.

        Window 1 runs from the 2020 map date to Q1 2025, the reference date of the 2025
        map edition. Its 2020 weight is the plants added after the 2020 map was
        compiled,
        not the whole of 2020, because the map is a mid-year snapshot.

        Window 2 runs from Q1 2025 to the June 2026 map date and covers exactly the
        plants the 2026 map draws in orange.

        Returns:
            tuple: the window 1 and window 2 additions per year.
        """
        plants_end_2020 = self.EU_PLANTS_EXISTING[2020] + self.EU_PLANTS_NEW[2020]
        plants_end_2025 = self.EU_PLANTS_EXISTING[2025] + self.EU_PLANTS_NEW[2025]
        window_1 = pd.Series(
            {
                2020: plants_end_2020 - int(self.get_plant_count_2020().sum()),
                2021: self.EU_PLANTS_NEW[2021],
                2022: self.EU_PLANTS_NEW[2022],
                2023: self.EU_PLANTS_NEW[2023],
                2024: self.EU_PLANTS_NEW[2024],
                2025: self.PLANTS_ADDED_Q1_2025,
            }
        )
        window_2 = pd.Series(
            {
                2025: self.EU_PLANTS_NEW[2025] - self.PLANTS_ADDED_Q1_2025,
                self.YEAR_LAST: sum(self.PLANTS_TOTAL_2026.values()) - plants_end_2025,
            }
        )
        return window_1, window_2

    def get_plant_additions(self) -> pd.DataFrame:
        """
        Modelled plant additions per node and year, from the 2020 map date to mid-2026.

        A node's plants added over the whole period is the difference between the two
        map
        counts. The orange plants of the 2026 map date that difference for the recent
        window; the remainder is spread over the earlier window with the European yearly
        profile. Nodes that shrank (SE, NO, LU) or whose orange count exceeds their net
        change (AT) get zero for the earlier window, so these are gross additions - see
        get_closures for what that leaves out.

        Returns:
            pd.DataFrame: nodes as rows, years as columns.
        """
        window_1, window_2 = self.get_year_weights()
        share_1 = window_1 / window_1.sum()
        share_2 = window_2 / window_2.sum()

        nodes = sorted(self.PLANTS_TOTAL_2026)
        plants_2026 = pd.Series(self.PLANTS_TOTAL_2026).reindex(nodes)
        plants_new = pd.Series(self.PLANTS_NEW_2026).reindex(nodes)
        plants_2020 = self.get_plant_count_2020().reindex(nodes).fillna(0)
        added_window_1 = (plants_2026 - plants_2020 - plants_new).clip(lower=0)

        additions = pd.DataFrame(
            np.outer(added_window_1, share_1), index=nodes, columns=share_1.index
        )
        for year, share in share_2.items():
            additions[year] = additions.get(year, 0.0) + plants_new * share
        return additions.sort_index(axis=1)

    def get_closures(self) -> pd.Series:
        """
        Plants per node that the two maps imply were closed, delisted or reclassified.

        A node whose 2026 count is below its 2020 count, or below the plants the 2026
        map
        itself flags as new, cannot have had only additions. That shortfall is reported
        here rather than netted off the additions.

        Returns:
            pd.Series: indexed by node.
        """
        nodes = sorted(self.PLANTS_TOTAL_2026)
        plants_2026 = pd.Series(self.PLANTS_TOTAL_2026).reindex(nodes)
        plants_new = pd.Series(self.PLANTS_NEW_2026).reindex(nodes)
        plants_2020 = self.get_plant_count_2020().reindex(nodes).fillna(0)
        return (plants_new - (plants_2026 - plants_2020)).clip(lower=0)

    def get_capacity_additions_2026(self) -> pd.Series:
        """
        Modelled capacity additions per node and year after the 2020 map [Nm3/h].

        Returns:
            pd.Series: indexed by node and year_construction.
        """
        average_2026, _ = self.get_average_capacity_2026()
        capacity = self.get_plant_additions().mul(average_2026, axis=0)
        capacity = capacity.stack()
        capacity.index.names = ["node", "year_construction"]
        return capacity.rename("capacity_existing")

    # -------- methods ------------------------
    def get_capacity_existing(
        self, element: ConversionTechnology, extend_to_2026: bool = True
    ) -> pd.Series:
        """
        Get the existing capacity for biomethane conversion technologies.

        Up to the 2020 map date the capacities are the ones the 2020 map reports for
        each
        plant. After it they are modelled from the 2026 map: plant counts per country,
        allocated to years with the European yearly profile on that map and valued with
        an
        average capacity per plant. Both parts land in the same series, so 2020 holds
        the
        plants the 2020 map dates to 2020 plus the modelled remainder of that year, and
        2026 covers H1 only.

        Args:
            element: The element for which to get the existing capacity.
            extend_to_2026: If False, return the 2020 map on its own, as before.

        Returns:
            pd.Series: A pandas Series containing the existing capacity data.
        """
        lhv = self.DEFAULT_LHV_BIOMETHANE  # kWh/m3
        capa = self.get_capacity_existing_2020()
        if extend_to_2026:
            capa = capa.add(self.get_capacity_additions_2026(), fill_value=0)
        capa *= lhv / 1e6
        capa = format_capacity_existing(capa)

        attr = element.capacity_existing
        source = SourceInformation(
            description=(
                "The existing capacity of biomethane conversion is obtained from the "
                "European Biogas Association's biomethane production statistics. "
                "Capacities up to 2020 are per-plant values from the 2020 biomethane "
                "map. The 2026 map reports plant counts only, so additions after the "
                "2020 map are the difference between the two editions' counts, "
                "allocated to years with the European yearly profile printed on the "
                "2026 map and valued at an average capacity per plant calibrated to "
                "the 8.2 bcm/yr EBA reports for 2026."
            ),
            metadata=self.metadata,
        )
        attr.set_data(df=capa, source=source, unit="GW")
        return attr
