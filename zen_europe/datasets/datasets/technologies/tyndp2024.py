import numbers
from pathlib import Path

import pandas as pd

from zen_creator import Dataset, Element, Attribute, MetaData, SourceInformation


class TYNDP2024Dataset(Dataset[pd.DataFrame]):
    """
    Dataset for TYNDP 2024.
    Gets capacity data for different years and scenarios (NT, DE, GA).
    """
    name = "TYNDP2024"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            author=["ENTSO-E", "ENTSO-G"],
            publication_year=2025,
            title="TYNDP 2024: Europe's electricity infrastructure plan.",
            publication="-",
            url="https://2024.entsos-tyndp-scenarios.eu/download/"
        )

    def _set_path(self) -> Path | None:
        return Path(self.source_path) / "03-technology" / "TYNDP24_gens.xlsx"

    def _set_data(self) -> pd.DataFrame:
        """Load and preprocess the TYNDP 2024 CSV dataset."""
        data = pd.read_excel(self.path)
        data.columns = data.columns.str.strip()

        # Country codes need to be harmonized (GR -> EL, GB -> UK)
        data["Country"] = data["Country"].replace({"GR": "EL", "GB": "UK"})

        # MAP correctly fuel types to technology names
        tyndp_fuel_map = {
            "Battery-TSO": "battery",
            "Biomass": "biomass_plant",
            "Coal": "hard_coal_plant",
            "Lignite": "lignite_coal_plant",
            "GasCC": "natural_gas_turbine",
            "GasCC-Syn": "natural_gas_turbine",
            "GasSC": "natural_gas_turbine",
            "Nuclear": "nuclear",
            "Oil": "oil_plant",
            "PV-roof": "photovoltaics",
            "Dam": "reservoir_hydro",  
            "RoR": "run-of-river_hydro",
            "Pump-Open": "pumped_hydro",
            "WindOff": "wind_offshore",
            "WindOn": "wind_onshore",
        }
        
        # if fuel type is not in the map, keep original value (e.g., for waste_plant)
        data["Fuel"] = data["SubType"].map(lambda x: tyndp_fuel_map.get(x, x))

        return data

    # ===================================================================
    # Method: get_capacity
    # ===================================================================
    def get_capacity(self, element: Element, scenario: str = "NT", year: int = 2030, climate_year: int = 2009, **kwargs) -> Attribute:
        """
        Returns capacity for a specific scenario and year.
        
        Expected format in ZEN-creator:
        MultiIndex (node, year) + column 'capacity_existing' in GW.
        
        Keywords:
            scenario (str): "NT" (National Trends), "DE" (Distributed Energy), "GA" (Global Ambition)
            year (int): e.g., 2030, 2040, 2050
            climate_year (int): climate year, most commonly 1995, 2008 or 2009.
        """
        tech_name = element.name
        
        # filter dataset for the given scenario, year, climate year and technology
        cond_active = (
            (self.data["Policy"] == scenario) &
            (self.data["start_year"] == year) &
            (self.data["Climate Year"] == climate_year) &
            (self.data["Fuel"] == tech_name)
        )
        df_tech = self.data[cond_active].copy()

        if df_tech.empty:
            df_capacity = pd.DataFrame(columns=["node", "year", "capacity_existing"])
            df_capacity = df_capacity.set_index(["node", "year"])
        else:
            df_capacity = df_tech[["Country", "start_year", "P_gen_max in 2015 (MW)"]].rename(columns={
                "Country": "node",
                "start_year": "year",  
                "P_gen_max in 2015 (MW)": "capacity_existing"
            })

            # switch from MW to GW and handle non-numeric values (e.g., if there are any missing or non-numeric entries, they will be set to 0)
            df_capacity["capacity_existing"] = pd.to_numeric(
                df_capacity["capacity_existing"], errors="coerce"
            ).fillna(0) / 1000.0

            # summarize capacities by node and year (in case there are multiple entries for the same node-year combination)
            df_capacity = (
                df_capacity.groupby(["node", "year"], as_index=False)["capacity_existing"]
                .sum()
            )
            
            # set multi-index
            df_capacity = df_capacity.set_index(["node", "year"])

        attr = Attribute("capacity", element)
        attr.set_data(
            df=df_capacity,
            unit="GW",
            source=SourceInformation(
                description=f"Capacities extracted from TYNDP2024 for Scenario {scenario}, Year {year}, Climate Year {climate_year}.",
                metadata=self.metadata 
            ),
        )
        return attr