# Changelog

This file gets automatically updated in ZEN-europe's continuous integration 
procedures. Do not edit the file manually.

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