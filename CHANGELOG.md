# Changelog

This file gets automatically updated in ZEN-europe's continuous integration 
procedures. Do not edit the file manually.

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