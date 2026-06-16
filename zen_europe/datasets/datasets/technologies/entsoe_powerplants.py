from pathlib import Path

import pandas as pd
from zen_creator import Attribute, Dataset, Element, MetaData, SourceInformation


class EntsoePPDataset(Dataset[pd.DataFrame]):
    """
    Dataset for power plant data from ENTSO-E used in 2025.
    """

    name = "entsoe_powerplants2025"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,  # Use the class attribute "entsoe_powerplants2025"
            author=["ENTSO-E"],
            publication_year=2026,
            title="Technology lifetimes and availability data for ESM",
            publication="Journal of Reliability and Risk Engineering",
            url="https://example.com/dataset.csv",
        )

    def _set_path(self) -> Path | None:
        return Path(self.source_path) / "03-technology" / "generator_data.xlsx"

    def _set_data(self) -> pd.DataFrame:
        """Load and preprocess ENTSO-E PP data for year 2025."""
        data = pd.read_excel(self.path, sheet_name="PP_data")
        data["Country"] = data["ISO"].replace({"GB": "UK", "GR": "EL"})

        data["DateIn"] = pd.to_numeric(data["DateIn"], errors="coerce")
        data["DateOut"] = pd.to_numeric(data["DateOut"], errors="coerce")

        # Only keep plants that are operating in 2025
        cond_active = (
            ((data["DateIn"] <= 2025) | data["DateIn"].isna())
            & ((data["DateOut"] > 2025) | data["DateOut"].isna())
            & (data["Status"] == "Operating")
        )
        df_pp = data[cond_active].copy()

        # Fuel → Technology mapping
        pp_fuel_map = {
            "Battery": "battery",
            "Biomass & Waste": "biomass_plant",
            "Coal Hard": "hard_coal_plant",
            "Coal Lignite": "lignite_coal_plant",
            "Natural Gas": "natural_gas_turbine",
            "Nuclear": "nuclear",
            "Oil": "oil_plant",
            "Process Gas": "natural_gas_turbine",
            "Solar": "photovoltaics",
        }
        df_pp["Fuel"] = df_pp["Fueltype"].map(pp_fuel_map)

        # Wind + Hydro need Technology column as well
        tech_map = {
            "Storage Hydro": "reservoir_hydro",
            "Run-of-River Hydro": "run-of-river_hydro",
            "Pumped Storage": "pumped_hydro",
            "Wind Onshore": "wind_onshore",
            "Wind Offshore": "wind_offshore",
        }
        tech_dependent_mask = df_pp["Fueltype"].isin(["Wind", "Hydro"])
        df_pp.loc[tech_dependent_mask, "Fuel"] = df_pp.loc[
            tech_dependent_mask, "Technology"
        ].map(tech_map)

        # Biomass/Waste 80/20 split (as in your ZEN-garden run)
        mask_bw = df_pp["Fueltype"] == "Biomass & Waste"
        df_waste = df_pp[mask_bw].copy()

        df_pp.loc[mask_bw, "Fuel"] = "biomass_plant"
        df_pp.loc[mask_bw, "Capacity"] = df_pp.loc[mask_bw, "Capacity"] * 0.8

        df_waste["Fuel"] = "waste_plant"
        df_waste["Capacity"] = df_waste["Capacity"] * 0.2

        df_pp = pd.concat([df_pp, df_waste], ignore_index=True)

        return df_pp

    # ===================================================================
    # New method: get_capacity
    # ===================================================================
    def get_capacity(self, element: Element, **kwargs) -> Attribute:
        """
        Returns existing capacity (2025) in the exact format ZEN-creator expects:
        MultiIndex (node, year_construction) + column 'capacity_existing' in GW.
        """
        tech_name = element.name
        df_tech = self.data[self.data["Fuel"] == tech_name].copy()

        if df_tech.empty:
            df_capacity = pd.DataFrame(
                columns=["node", "year_construction", "capacity_existing"]
            )
        else:
            df_capacity = df_tech[["Country", "DateIn", "Capacity"]].rename(
                columns={
                    "Country": "node",
                    "DateIn": "year_construction",
                    "Capacity": "capacity_existing",
                }
            )

            # MW → GW
            df_capacity["capacity_existing"] = (
                pd.to_numeric(df_capacity["capacity_existing"], errors="coerce")
                / 1000.0
            )

            # unknown construction year → 2025
            df_capacity["year_construction"] = pd.to_numeric(
                df_capacity["year_construction"], errors="coerce"
            ).fillna(2025)

            # sum up capacities for plants
            df_capacity = df_capacity.groupby(
                ["node", "year_construction"], as_index=False
            )["capacity_existing"].sum()
            # set multi-index
            df_capacity = df_capacity.set_index(["node", "year_construction"])

        attr = Attribute(
            "capacity_existing",
            element=element,
            df=df_capacity,
            unit="GW",
            default_value=0.0,
            source=SourceInformation(
                description="Existing capacities extracted from ENTSO-E 2025 dataset.",
                metadata=self.metadata,
            ),
        )
        return attr
