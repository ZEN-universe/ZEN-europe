from pathlib import Path
import pandas as pd
import numpy as np
from zen_creator.model import Model
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.datasets.datasets.metadata import SourceInformation
from zen_creator.datasets.datasets.entsoe_powerplants import EntsoePPDataset 
from zen_creator.datasets.datasets.tyndp2024 import TYNDP2024Dataset


# 3) Load new dataset

thesis_metadata = MetaData(
    name="thesis_modifications",
    author=["Joel"], # Remember, author must be a list!
    publication_year=2026,
    title="Manual modifications for Master Thesis",
    publication="ETH Zurich",
    url=""
)

# 4) Change parameters
# ================================================
# 4.1 Only for technologies in technology_list: set capacity_existing based on new dataset
# ================================================
technology_list = ["battery", "biomass_plant", "hard_coal_plant", "lignite_coal_plant", "natural_gas_turbine", "nuclear", "oil_plant", 
                #"photovoltaics", 
                "reservoir_hydro", 
                "run-of-river_hydro", 
                "waste_plant", 
                "wind_offshore", 
                "wind_onshore", 
                "pumped_hydro"]
for tech_name in technology_list:
    if tech_name not in model.elements:
        continue
    technology = model.elements[tech_name]

    # Temporäres Attribut mit dem korrekten DataFrame erzeugen
    temp_attr = entsoe_ds.get_capacity(technology)
    
    technology.capacity_existing.set_data(
        df=temp_attr.df,           # the fully prepared MultiIndex DataFrame
        unit=temp_attr.unit,
        source=temp_attr.sources[0]
    )

    # Automated synchronization for storage (pumped storage & batteries)
    if hasattr(technology, "capacity_existing_energy"):
        # Select specific ratio
        if tech_name == "battery":
            ep_ratio = 2.0  # example: 2 hours of storage for batteries
        else:
            ep_ratio = 6.0  # Standard 6 hours for hydro storage, adjust as needed
        
        df_energy = pd.DataFrame({
            "capacity_existing_energy": temp_attr.df["capacity_existing"] * ep_ratio
        })
        
        technology.capacity_existing_energy.set_data(
            df=df_energy,
            unit="GWh",
            source=temp_attr.sources[0]
        )
        print(f"Synchronized: {tech_name} with {ep_ratio}")


# ================================================
# 4.2 lifetime has to be extended by +10 years for all fossil technologies 
# (to prevent early retirements due to the new dataset already including all active plants in 2025)
# ================================================
fossil_techs = ["hard_coal_plant", "lignite_coal_plant", "natural_gas_turbine", "oil_plant"]

for tech_name in fossil_techs:
    if tech_name not in model.elements:
        continue
        
    technology = model.elements[tech_name]
    
    if hasattr(technology, "lifetime"):
        attr = technology.lifetime
        
        # Grab the scalar default value (e.g., 46.0 for hard_coal_plant)
        base_lifetime = getattr(attr, "default_value", None)
        
        if base_lifetime is not None:
            new_lifetime = float(base_lifetime + 10) # Ensure it's a float for JSON compatibility
            
            # EXPLICITLY OVERWRITE THE DEFAULT VALUE
            # By skipping the .set_data() method and dataframe creation, 
            # ZEN-creator will only log this change in attributes.json and skip CSV creation.
            attr.default_value = new_lifetime
            
            print(f"Lifetime extended for {tech_name} from {base_lifetime} to {new_lifetime} in attributes.json")


# ================================================
# 4.3 Add capacity limits for 2025 (fixed to 0) and 2030 (TYNDP)
# ================================================
technology_list.append("photovoltaics")

for tech_name in technology_list:
    if tech_name not in model.elements:
        continue
        
    technology = model.elements[tech_name]

    # --- 1. Fetch Datasets & Extract Unique Locations ---
    entsoe_attr = entsoe_ds.get_capacity(technology)
    spatial_indices = [idx for idx in entsoe_attr.df.index.names if idx in ["location", "node", "edge"]]
    
    df_2025_base = entsoe_attr.df.copy().reset_index()
    locs_2025 = df_2025_base[spatial_indices].drop_duplicates() if not df_2025_base.empty else pd.DataFrame(columns=spatial_indices)
    
    tyndp_attr = tyndp_ds.get_capacity(technology, target_year=2030)
    df_2030_base = tyndp_attr.df.copy().reset_index()
    locs_2030 = df_2030_base[spatial_indices].drop_duplicates() if not df_2030_base.empty else pd.DataFrame(columns=spatial_indices)
    
    # Master list of all known locations across both years
    all_locs = pd.concat([locs_2025, locs_2030]).drop_duplicates()

    # --- 2. Build 2025 Capacity Limits (All Zeros) ---
    df_max_2025 = all_locs.copy()
    df_min_2025 = all_locs.copy()
    if not df_max_2025.empty:
        df_max_2025["year"] = 2025
        df_max_2025["capacity_limit"] = 0.0  # Forces delta_S = 0 in optimization
        
        df_min_2025["year"] = 2025
        df_min_2025["capacity_lower_limit"] = 0.0 

    # --- 3. Build 2030 Capacity Limits (TYNDP) ---
    if not df_2030_base.empty:
        if "year" not in df_2030_base.columns:
            df_2030_base["year"] = 2030
            
        # Upper Bounds
        upper_bound_values = df_2030_base["capacity_existing"] * 1.3
        upper_bound_values = upper_bound_values.where(df_2030_base["capacity_existing"] > 0, 0.1) 
        
        df_max_2030 = df_2030_base[spatial_indices + ["year"]].copy()
        df_max_2030["capacity_limit"] = upper_bound_values

        # Lower Bounds (70% of TYNDP)
        lower_bound_values = df_2030_base["capacity_existing"] * 0.7
        
        df_min_2030 = df_2030_base[spatial_indices + ["year"]].copy()
        df_min_2030["capacity_lower_limit"] = lower_bound_values
        
        # Combine
        df_max_combined = pd.concat([df_max_2025, df_max_2030], ignore_index=True)
        df_min_combined = pd.concat([df_min_2025, df_min_2030], ignore_index=True)
        source_to_use = tyndp_attr.sources[0]
    else:
        # Fallback if no 2030 data exists
        df_max_combined = df_max_2025
        df_min_combined = df_min_2025
        source_to_use = entsoe_attr.sources[0]

    # --- 4. Rebuild the Index & Set Data ---
    if not df_max_combined.empty:
        index_cols = spatial_indices + ["year"]
        df_max_combined.set_index(index_cols, inplace=True)
        df_min_combined.set_index(index_cols, inplace=True)

        if hasattr(technology, "capacity_limit"):
            technology.capacity_limit.set_data(
                df=df_max_combined,
                unit="GW",
                source=source_to_use
            )
            print(f"Combined Upper capacity limit set for {tech_name}")
            
        if hasattr(technology, "capacity_lower_limit"):
            technology.capacity_lower_limit.set_data(
                df=df_min_combined,
                unit="GW",
                source=source_to_use
            )
            print(f"Combined Lower capacity limit set for {tech_name}")

# ================================================
# 4.4 Fix Units for Non-Energy Technologies (like Steel/Chemicals)
# ================================================
for tech_name, element in model.elements.items():
    # Sync Power / Base Units
    if hasattr(element, "capacity_lower_limit") and hasattr(element, "capacity_limit"):
        element.capacity_lower_limit.unit = element.capacity_limit.unit
        
    # Sync Energy Units for Storage
    if hasattr(element, "capacity_lower_limit_energy") and hasattr(element, "capacity_limit_energy"):
        element.capacity_lower_limit_energy.unit = element.capacity_limit_energy.unit

# ================================================
# 4.5 Add small CAPEX for BEV and PHEV to prevent unnecessary capacity addition
# ================================================
ev_techs = ["BEV", "PHEV electric part"] 

for tech_name in ev_techs:
    if tech_name not in model.elements:
        continue
        
    technology = model.elements[tech_name]
    
    # ZEN-garden models usually use one of these attributes for CAPEX
    if hasattr(technology, "capex_specific_conversion"):
        attr = technology.capex_specific_conversion
        
        # Use a dummy float value. Depending on your units (e.g. M€/GW vs €/kW), 
        # 0.01 or 1.0 is generally small enough not to impact real economics 
        # but large enough to stop free over-investment.
        small_capex_penalty = 0.01 
        
        attr.default_value = small_capex_penalty
        print(f"Added small penalty CAPEX of {small_capex_penalty} to {tech_name} in attributes.json")


# 5) Validate and write files
model.write()

# ================================================
# 6) Post-write modifications & cleanup
# ================================================
print("\n--- Running Post-Write Actions ---")
new_model_path = model.output_folder / model.name
files_deleted = 0

if new_model_path.exists():
    for file_path in new_model_path.rglob("capacity_limit_yearly_variation.csv"):
        try:
            file_path.unlink()  
            print(f"Deleted: {file_path}")
            files_deleted += 1
        except Exception as e:
            print(f"Could not delete {file_path}: {e}")
            
if files_deleted == 0:
    print(f"No 'capacity_limit_yearly_variation.csv' files were found to delete in {model.name}.")
else:
    print(f"Successfully deleted {files_deleted} file(s) from {model.name}.")