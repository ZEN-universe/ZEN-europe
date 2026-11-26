# Changelog

This file gets automatically updated in ZEN-europe's continuous integration 
procedures. Do not edit the file manually.

## [v2.1.0] - 2026-11-26 

### Data Changes 📊
- reduce power line losses to more accurately reflect values in the literature. The previous losses amounted to 50% per 1000 km, which unrealistically taxed trade between countries. [[🔀 PR #66](https://github.com/ZEN-universe/ZEN-europe/pull/66) @csfunke]

## [v2.0.1] - 2026-11-26 

### Bug Fixes 🐛
- fix vulnerability in electrolysis cost implementation. The previous implementation, although correct, could have lead to bugs when both a default value and a data csv file are specified. [[🔀 PR #72](https://github.com/ZEN-universe/ZEN-europe/pull/72) @csfunke]

## [v2.0.0] - 2026-11-24 

### New Features ✨
- Add the sectors `glass`, `ceramic`, `paper` and `food`, each with a product carrier and a `<sector>_production` technology. The demand comes from JRC-IDEES-2023 physical output for glass and paper, from JRC-IDEES thermal energy divided by the Rehfeldt (2017) fuel intensity for ceramic, and from the Rehfeldt activity distributed by FAOSTAT production for food. CH, NO and UK are filled from proxy countries, JRC BAT Paper and BFE. Energy intensities come from AIDRES and Rehfeldt, the split of the 100–200 °C demand into bands from Wolf (2017), and lifetimes from JRC-EU-TIMES. First implementation by @hangoe in #69. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Add the shared `industrial_heat` sector with the heat carriers `heat_industry_0_100`, `heat_industry_100_150` and `heat_industry_150_200`. It contains six industrial boilers (DEA Technology Data for Industrial Process Heat), heat pumps per band with a water or a waste-heat source (COP at 0.5 × Carnot, source temperatures from Bever 2024), and a lossless temperature cascade. The existing boiler fleet follows the JRC-IDEES fuel mix per country, or BFE for CH. The heat pumps diffuse as `heat_pump_DH`, with an unbounded seed. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Add the carrier `recoverable_waste_heat`. Industrial processes now output their recoverable exhaust heat, from sEEnergies D5.1: the natural gas and hydrogen furnace fuels of glass and ceramic, `cement_production`, `paper_production`, `food_production`, `BF_BOF`, `EAF`, `NG_DRI` and `H2_DRI`. The waste-heat heat pumps and the new `waste_heat_integration_DH` use this heat, with the recovery cost of Stark et al. (2025). The new setting `operation.use_industrial_waste_heat` (default `true`) switches it off. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Add kiln fuel switching for glass and ceramic through the retrofits `{natural_gas,hydrogen,electricity}_to_{glass,ceramic}_fuel`, and post-combustion capture through `glass_post_comb` and `ceramic_post_comb`. The fuel conversion factors are AIDRES route ratios. Hydrogen and electricity can cover at most 97.4 % of the ceramic fuel (ceramic BREF, Rehfeldt). The capture data are DEA 401.c values, with `cement_post_comb` as the proxy. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Connect the process heat of existing technologies to the industrial heat bands. `DAC`, `anaerobic_digestion` and `biomethane_conversion` now use `heat_industry_0_100` instead of `heat`. `haber_bosch`, `gasification`, `pyrolysis`, `methanol_from_biomass`, `fischer_tropsch` and `methanol_from_hydrogen` exchange the 100–150 °C or 150–200 °C band instead of `district_heat` or `heat`. `electrolysis` and the CCS retrofits output `recoverable_waste_heat`. `SMR_CCS`, `natural_gas_turbine_CCS` and `biomass_plant_CCS` take `heat_industry_100_150`, with conversion factors from the DEA carbon capture catalogue (100 MW(th) WtE or biomass CHP retrofit as the proxy). [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Add the emissions of the new sectors to the carbon budget. For the EU, these are EEA codes 1.A.2.d (paper) and 1.A.2.e (food). For the UK, they are the DESNZ categories for glass, bricks and other ceramics, plus a new `ONSIndustryEmissions` dataset for paper and food. Each UNFCCC code is now counted only once. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]

### Bug Fixes 🐛
- Derive the capacity limits, maximum loads and inflows of nuclear, hydropower and carbon storage from today's fleet instead of `capacity_existing`, so that they no longer drop to zero with `investment.use_existing_capacities: false`. Also, `pumped_hydro` now resets `capacity_existing_energy` (instead of `capacity_existing`) when existing capacities are off. A new unit test checks that every setter of the existing capacity and of the maximum diffusion rate respects its investment switch. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Make every valid sector selection contain the carriers and technologies its elements use. The new sector `oil_products` holds diesel, gasoline, kerosene and naphtha, and transport, shipping and refining now require it. `diesel_ICE_ship` is removed from `refining`, `methanation` and `fischer_tropsch` are added to `carbon`, and the sectors whose technologies use the industrial heat carriers now require `industrial_heat`. A new unit test builds the smallest valid selection for each element. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- List in `sources.md` only the datasets an attribute actually reads, instead of every dataset of the collection. The technology cost database now also records which agencies reported data. This relies on the usage tracking of ZEN-creator 3.1.0. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]

### Documentation Changes 📝
- Describe the new industry sectors and `industrial_heat` in the structure page and the `operation` settings in the tutorials. Enable MyST heading anchors and fix the documentation badge in the README. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]

### Maintenance Tasks 🧹
- Require `zen-creator>=3.1.0`, which provides `instance_cache` and the tracking of the datasets read per attribute. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Add a weekly GitHub workflow that checks the reachability of all URLs that datasets cite or download from, and reports dead links in one issue. The URL tests live in `tests/network` and are deselected by default through the `network` marker. A unit test also checks that every dataset has a URL or a DOI. Outdated URLs in the dataset metadata are fixed. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Stop committing derived caches (JRC-IDEES industry and passenger car feathers, Eurostat queries, processed DEA data). They are now registered in `CACHE_PROVIDERS`, and the ENSPRESO 2 download gets its own cache with an `overwrite_enspreso2_offshore` flag. Superseded raw files are removed. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Remove unused datasets and methods: `WorldBankCO2Emissions`, `GlobalCCSInstitute`, `JRCHydroDB`, the all-GHG variants of the EEA and DESNZ inventories, `TechnologyCostDatabase.export_cost_table`, `CCSConversionFactor.get_conversion_factor_CCS` and unused Eurostat queries. `instance_cache` now comes from ZEN-creator. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Add unit constants (`GJ_PER_GWH`, `GJ_PER_KTOE`, `GWH_PER_KTOE`, `KELVIN_AT_ZERO_CELSIUS`, `KT_PER_GT`, …) and a shared `ISO2_TO_NODE` mapping, and use them instead of literals. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]

### Data Changes 📊
- Take the offshore wind potential from the fixed-bottom reference potential of ENSPRESO 2 per exclusive economic zone, and the profile from the PECD existing-technology turbine. Nodes without existing offshore wind farms use the PECD future-turbine profile, scaled down to existing full load hours. Together, the high ENSPRESO v1 potential and the future-turbine profile had made the model overbuild offshore wind. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Take the onshore wind potential from the ENSPRESO 2 with 500 m distance rule. The ENSPRESO 1 high scenario was a technical potential and didn't align with realistic capacity limits. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Base the steel demand on Eurofer crude steel production (2020–2024 mean; worldsteel 2024 for PT and UK) instead of AIDRES, and split it by route per node. The secondary (EAF) share starts at the 2024 electric arc furnace share of each node (worldsteel; Global Iron and Steel Tracker for CH and NO). It rises linearly to at least the 60 % end share of Material Economics in 2050. The existing `BF_BOF` and `EAF` capacities follow this split per node. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Base the passenger mileage demand on the vehicle-km driven by passenger cars in the time series year. The sources are JRC-IDEES for the EU27, DfT TRA0101 for the UK, BFS for CH and SSB for NO. This replaces the passenger-km of the Statistical Pocketbook divided by an assumed EU average occupancy. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]

### BREAKING CHANGES ⚠️
- Rename the settings category `max_load` to `operation` (`MaxLoadSettings` to `OperationSettings`). Configurations that set `max_load.use_seasonal_nuclear_max_load` or `max_load.use_nodal_nuclear_max_load` must now use `operation.*`. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]
- Rename `cement_kiln` to `cement_production` and `fuel_for_cement` to `cement_fuel`, to match the other production sectors. Scenario files and analyses that use the old names must be updated. [[🔀 PR #70](https://github.com/ZEN-universe/ZEN-europe/pull/70) @jacob-mannhardt]

## [v1.6.0] - 2026-10-30 

### Bug Fixes 🐛
- avoid numerical issues/demand shedding in olefin [[🔀 PR #62](https://github.com/ZEN-universe/ZEN-europe/pull/62) @jacob-mannhardt]

### Data Changes 📊
- add 40% more existing capacity for SMR because of the 70% utilization from the European Hydrogen Observatory. [[🔀 PR #62](https://github.com/ZEN-universe/ZEN-europe/pull/62) @jacob-mannhardt]

## [v1.5.2] - 2026-10-29 

### Bug Fixes 🐛
- Fix ENTSOE error message when API key is missing. Now it highlights that the user needs to send an email [[🔀 PR #60](https://github.com/ZEN-universe/ZEN-europe/pull/60) @jacob-mannhardt]
- Rewrite the documentation where it mistakenly said ZEN-creator and remove redundant files [[🔀 PR #60](https://github.com/ZEN-universe/ZEN-europe/pull/60) @jacob-mannhardt]

## [v1.5.1] - 2026-10-29 

### Bug Fixes 🐛
- fix default value for `capacity_existing_energy` of `reservoir_hydropower` and `pumped_hydropower`. The default value was still set tin `Inf` in countries that did not have existing capacity for these hydropower types.. [[🔀 PR #58](https://github.com/ZEN-universe/ZEN-europe/pull/58) @csfunke]

## [v1.5.0] - 2026-10-28 

### New Features ✨
- Add switch (`settings.emissions.correct_budget_with_global_emissions`) to indicate whether to calculate the carbon budget as: `2020 global budget -> subtract past global emissions for e.g., 2026 global budget -> European share` or `2020 global budget -> European share -> subtract past European emissions for e.g., 2026 European budget` (lower than the former). [[🔀 PR #56](https://github.com/ZEN-universe/ZEN-europe/pull/56) @jacob-mannhardt]

### Bug Fixes 🐛
- Extrapolate the historic emissions for years before the reference year that are not included in the data. Provides a warning if some years are not covered (Error if `settings.emissions.extrapolate_missing_years=False`) [[🔀 PR #56](https://github.com/ZEN-universe/ZEN-europe/pull/56) @jacob-mannhardt]

### Documentation Changes 📝
- add the link to the read the docs to the readme to find the RtD [[🔀 PR #53](https://github.com/ZEN-universe/ZEN-europe/pull/53) @jacob-mannhardt]
- add link to the Read the Docs in the README. [[🔀 PR #51](https://github.com/ZEN-universe/ZEN-europe/pull/51) @csfunke]

### Maintenance Tasks 🧹
- fix the series name in `carbon_emissions_annual_limit` [[🔀 PR #56](https://github.com/ZEN-universe/ZEN-europe/pull/56) @jacob-mannhardt]

## [v1.4.0] - 2026-10-20 

### Data Changes 📊
- update the hydropower data. The data is now taken from only two sources: the Pan-European Climate database (accessed via the Copernicus api) and the harmonized Pan-European Climate database capacities published on Zenodo under `https://zenodo.org/records/3985078/files/`. The new data now include inflows from run-of-river hydropower plants with pondage and open-loop pumped hydropower, thereby ensuring the inflows are complete. Energy and power capacities, as well as inflows from open-loop pumped hydropower, are divided into reservoir hydropower and closed-loop pumped hydropower. This means that pumped hydropower is no longer purely a storage technology but also has some inflows. Finally, run-of-river inflows for Finland and Norway are moved to reservoir hydropower inflows to ensure consistency between the capacity and inflow datasets. [[🔀 PR #49](https://github.com/ZEN-universe/ZEN-europe/pull/49) @csfunke]

## [v1.3.0] - 2026-10-15 

### New Features ✨
- speeding up the querying of ENTSOE by parallelizing it [[🔀 PR #47](https://github.com/ZEN-universe/ZEN-europe/pull/47) @jacob-mannhardt]

## [v1.2.0] - 2026-10-14 

### Bug Fixes 🐛
- remove the `system.use_capacities_existing` setting when setting `use_existing_capacities=False`, because this does not allow for keeping existing hydro capacities. And there is no need to set `system.use_capacities_existing`, because we don't produce any existing capacities for any other technologies anyway. [[🔀 PR #45](https://github.com/ZEN-universe/ZEN-europe/pull/45) @jacob-mannhardt]

### Data Changes 📊
- Calculate the more expensive DAC from Sievert et al. The cost per cumulative capacity is converted to a yearly trajectory by utilizing various projections of global DAC deployment. [[🔀 PR #45](https://github.com/ZEN-universe/ZEN-europe/pull/45) @jacob-mannhardt]

## [v1.1.0] - 2026-10-14 

### New Features ✨
- separate `price_year` from `reference_year` so that the two can be specified independently. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]
- add output folder to command line options. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]
- add `clear_caches` command line flag which allows a complete rerun of ZEN-europe. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]

### Bug Fixes 🐛
- remove cached files so that the main branch contains only raw data. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]
- make the Eurostat API more robust by retrying each query multiple times, setting a limit on the maximum number of workers, and differentiating between failed requests and empty data. This fixes consistency issues with the Eurostat API, which frequently failed. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]
- fix bug in Eurostat which caused years to be stored as objects rather than integers. This caused the code to produce an empty DataFrame error when loading Eurostat data without a cache. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]
- update dea api to match new spreadsheet format. [[🔀 PR #41](https://github.com/ZEN-universe/ZEN-europe/pull/41) @csfunke]

## [v1.0.1] - 2026-10-13 

### Bug Fixes 🐛
- fix setup for read the docs [[🔀 PR #36](https://github.com/ZEN-universe/ZEN-europe/pull/36) @jacob-mannhardt]

### Documentation Changes 📝
- Fix the name of the docs from ZEN-creator to ZEN-europe. [[🔀 PR #34](https://github.com/ZEN-universe/ZEN-europe/pull/34) @jacob-mannhardt]

## [v1.0.0] - 2026-10-12 

### Maintenance Tasks 🧹
- upgrade `black` to patch security vulnerability. [[🔀 PR #20](https://github.com/ZEN-universe/ZEN-europe/pull/20) @csfunke]

### Data Changes 📊
- Full energy system v1 [[🔀 PR #31](https://github.com/ZEN-universe/ZEN-europe/pull/31) @jacob-mannhardt]

### BREAKING CHANGES ⚠️
- This is the first full energy system [[🔀 PR #31](https://github.com/ZEN-universe/ZEN-europe/pull/31) @jacob-mannhardt]

## [v0.3.0] - 2026-06-12 

### Data Changes 📊
- adds ENSPRESO dataset for import availabilities of biomass and wet_biomass. [[🔀 PR #17](https://github.com/ZEN-universe/ZEN-europe/pull/17) @csfunke]

## [v0.2.0] - 2026-06-05 

### New Features ✨
- import and register ZEN-europe's custom components [[🔀 PR #15](https://github.com/ZEN-universe/ZEN-europe/pull/15) @manud99]
- add config file to register custom component such as `energy_system_nuts0` [[🔀 PR #15](https://github.com/ZEN-universe/ZEN-europe/pull/15) @manud99]
- add DVC to track large data files. [[🔀 PR #15](https://github.com/ZEN-universe/ZEN-europe/pull/15) @manud99]

## [v0.1.0] - 2026-04-28 

### New Features ✨
- add feedback to CLI output. [[🔀 PR #11](https://github.com/ZEN-universe/ZEN-europe/pull/11) @manud99]
- replace underscore with dash in CLI arguments. [[🔀 PR #11](https://github.com/ZEN-universe/ZEN-europe/pull/11) @manud99]

## [v0.0.2] - 2026-04-28 

### Bug Fixes 🐛
- update to match the syntax of ZEN-creator v1.2.0. [[🔀 PR #12](https://github.com/ZEN-universe/ZEN-europe/pull/12) @csfunke]

### Maintenance Tasks 🧹
- remove unnecessary zen-europe folder containing test outputs. [[🔀 PR #5](https://github.com/ZEN-universe/ZEN-europe/pull/5) @ZEN-robot]
- fix automatic changelog update in continuous integration procedure. [[🔀 PR #3](https://github.com/ZEN-universe/ZEN-europe/pull/3) @csfunke]

## [v1.0.0] - 2026-04-08 

### BREAKING CHANGES ⚠️
- Release first public version of ZEN-europe on Py-PI.