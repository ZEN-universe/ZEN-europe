from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class ENTSOG(Dataset[pd.DataFrame]):
    """
    ENTSOG dataset class for natural gas availability.

    This class implements the specific behavior for the ENTSOG dataset.
    """

    name = "entsog"
    _TWh2bcm = 0.10236

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Extra EU supply potentials TYNDP 2022"),
            author=["ENTSOG"],
            publication="ENTSOG",
            publication_year=2022,
            url="https://www.entsog.eu/sites/default/files/2021-05/7_ENTSOG%20-%20Extra%20EU%20supply%20potentials%20part%201.pdf",
            note=(
                "We use the April 2022 update of the extra supply potentials from "
                "ENTSOG. The data is available in the TYNDP 2022 dataset."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "02-carrier"
            / "natural_gas"
            / "220404_Updated_Gas_Data.xlsx"
        )

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_excel(self.path, sheet_name="EU CH4 Supply Potentials")
        data["Year"] = data["Year"].dt.year
        data = data.set_index(["Supply source", "Year", "Parameter"])
        # sums Min + Range -> maximum available supply potential
        agg_data = data.groupby(level=["Supply source", "Year"]).sum()
        agg_data = agg_data * 1000 / self._TWh2bcm  # convert to GWh
        return cast(pd.DataFrame, agg_data.unstack())

    def get_availability_natural_gas(self) -> pd.DataFrame:
        """
        Get the natural gas availability data.

        This function retrieves the natural gas availability data from the ENTSOG
        dataset.
        """
        return self.data.copy()


class ENTSOGTransmissionCapacityMap(Dataset[pd.DataFrame]):
    """
    ENTSOG Transmission Capacity Map dataset class for natural gas.

    This class implements the specific behavior for the ENTSOG Transmission Capacity Map
    dataset.
    """

    name = "entsog_transmission_capacity_map"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("ENTSOG Transmission Capacity Map 2021"),
            author=["ENTSOG"],
            publication="ENTSOG",
            publication_year=2021,
            url="https://www.entsog.eu/maps#transmission-capacity-map-2021",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()  # Placeholder for actual data loading logic

    def _get_additional_gas_import_capacity(self) -> tuple[pd.DataFrame, pd.Series]:
        """
        Get the additional gas import capacity data.

        returns additional essential gas import capacity that is
        not yet part of the SciGrid Database. Also returns if the connection is
        from/to Russia.
        """
        manual_gas_limit = pd.DataFrame(columns=["import", "export"])
        manual_gas_limit.loc["BG"] = [24, 0]
        manual_gas_limit.loc["EL"] = [14.583, 0]
        is_russian = pd.Series(dtype=bool)
        is_russian["BG"] = True
        is_russian["EL"] = False
        return manual_gas_limit, is_russian

    def adjust_by_additional_gas_import(
        self, import_gas: pd.DataFrame, import_gas_RU: pd.Series
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Adjust the import gas data by additional gas import capacity.

        This function adjusts the import gas data by adding additional gas import
        capacity
        that is not yet part of the SciGrid Database.
        """
        manual_gas_capacities, is_russian = self._get_additional_gas_import_capacity()
        for idx_manual_gas_capacity in manual_gas_capacities.index:
            if idx_manual_gas_capacity in import_gas.index:
                import_gas.loc[idx_manual_gas_capacity] += manual_gas_capacities.loc[
                    idx_manual_gas_capacity
                ]
            else:
                import_gas = pd.concat(
                    [import_gas, manual_gas_capacities.loc[idx_manual_gas_capacity]]
                )
                import_gas.index.name = "node"
            if is_russian[idx_manual_gas_capacity]:
                if idx_manual_gas_capacity in import_gas_RU.index:
                    import_gas_RU.loc[
                        idx_manual_gas_capacity
                    ] += manual_gas_capacities.loc[idx_manual_gas_capacity]
                else:
                    import_gas_RU = pd.concat(
                        [
                            import_gas_RU,
                            manual_gas_capacities.loc[
                                [idx_manual_gas_capacity], "import"
                            ],
                        ]
                    )
                    import_gas_RU.index.name = "node"
        import_gas = import_gas.sort_index()
        import_gas_RU = import_gas_RU.sort_index()
        return import_gas, import_gas_RU
