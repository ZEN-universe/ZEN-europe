# Industry heat sectors

*Note: this documentation page is not intended for the PR on ZEN-universe; it is
included for the completeness of the submission.*

Sectors `glass`, `ceramic`, `paper` and `food` (`zen_europe/elements/sectors/`).
Input data are computed in `IndustryProductionData` (`industry_production_data.py`) and
`IndustryHeatSupply` (`industry_heat_supply.py`) in `zen_europe/datasets/dataset_collections/`.

## Structure

- **Sectors**: glass, ceramic, paper, food. Each has a product carrier and a
  `<sector>_production` technology. Cement, steel and chemicals are part of the main model.
  `ceramic` covers the JRC-IDEES subsector *Ceramics & other non-metallic minerals*
  (also lime, gypsum, mineral wool; see [Ceramic](#ceramic)).
- **Heat bands**: heat < 200 °C is split into `heat_industry_{0_100,100_150,150_200}_<sector>`,
  so heat pump efficiency (COP) depends on the band. Heat > 200 °C is a direct fuel input
  of the production technology.
- **Per-sector heat chain**: each sector holds its own boilers, heat pumps, cascade, kiln
  fuel, TES and DSM (`<name>_<sector>`), so heat cannot be exchanged between sectors.
- **Default dataset**: the four sectors are part of the default `structure.set_sectors`
  in `zen_europe/settings/structure.py`; the `zen_europe_legacy` model in
  `data/models.yaml` removes them.
- **Sector links**: `glass` and `ceramic` require `electricity`, `gas`, `hydrogen` (kiln
  fuel) and `district_heating`; `paper` and `food` require `electricity`, `gas` and
  `district_heating`. `glass_post_comb` and `ceramic_post_comb` are also declared by
  `carbon` and `cement` and only added when both are active. Each `*_DSM` is declared by
  the sector of its product (`glass`, `ceramic`, `paper`, `food`, `ammonia`, `cement`,
  `methanol` or `steel`).

### Settings (`industry_flexibility.*`, `zen_europe/settings/industry_flexibility.py`)

Technologies that are switched off are removed from the model before it is built
(`remove_inactive_industry_elements` in `zen_europe/model_creator.py`).

| setting | default | use |
|---|---|---|
| `use_tes` | `true` | thermal energy storage of the four sectors |
| `dsm_shiftability` | `optimistic` | DSM category column; `none` removes the DSM of all industrial products |
| `heat_pump_temp_levels` | all three bands | bands with industry heat pumps |

### General assumptions

Own numeric assumptions of the industry sectors (heat pump COP, waste-heat recovery cost,
process CO2, kiln switchable share, the technical parameters of the temperature
cascade, TES and DSM, the fuel share cut-off, the boiler capacity cut-off, the capacity
limit margin and the heat pump diffusion parameters) are in
`data/raw_data/03-technology/industry/general_assumptions_industries.csv`
(`IndustryGeneralAssumptions`), each with its reasoning and sources. The year of the
production, energy and heat statistics is `DATA_YEAR` (2023) in
`zen_europe/utils/industry.py`.

### Scenarios (`data/models.yaml`, generated with `zen-europe --all`)

| scenario | change |
|---|---|
| default: four sectors, full flexibility (TES and DSM) | `zen_europe` |
| original ZEN-europe (no industrial heat, TES or DSM) | `zen_europe_legacy`: removes the four sectors, `use_tes: false`, `dsm_shiftability: none` |
| no flexibility | `use_tes: false`, `dsm_shiftability: none` |
| TES only / DSM only | `dsm_shiftability: none` / `use_tes: false` |
| no diffusion | no flexibility with `investment.use_diffusion_rates: false` |
| DSM pessimistic | DSM only with `dsm_shiftability: pessimistic` |
| single temperature (`_single_temp`) | `heat_pump_temp_levels: ["150_200"]`. Lower bands are served via the cascade |

## Product demand and existing capacity

Demand (t/h) = annual physical production ÷ 8760 h, flat over the year. Net trade is not
modeled. Existing boilers, the cascade, the waste heat limit and the kiln fuel are all
based on this demand. Existing production capacity (t/h) = installed capacity ÷ 8760 h
where JRC-IDEES reports it (glass, paper: about 26–29 % headroom above demand) and demand ÷
`capacity_utilisation` (0.8, from the glass and paper ratio, 25 % headroom) otherwise, so
DSM can use existing plants.

| sector | demand basis | existing capacity basis |
|---|---|---|
| glass, paper | JRC-IDEES-2023 physical output | JRC-IDEES-2023 installed capacity |
| ceramic | JRC-IDEES thermal final energy ÷ Rehfeldt weighted fuel intensity | demand ÷ 0.8 |
| food | Rehfeldt EU28+3 activity per sub-process, distributed to nodes by FAOSTAT production of a proxy item (`FOOD_ITEMS`) | demand ÷ 0.8 |

**Nodes without JRC-IDEES** (CH, NO, UK; `NODES_WITHOUT_IDEES`):

- glass, ceramic: CH = AT, NO = FI, UK = DE × population UK/DE in `DATA_YEAR`
  (World Bank, `WorldBankPopulation`);
- paper: 2008 *consumption* from JRC BAT Paper (2015), Table 1.2 (CH 1,397, NO 831,
  UK 11,443 kt), used as demand; existing capacity = demand ÷ 0.8. No existing boilers at these nodes;
- food: FAOSTAT covers all nodes.

**Vintages**: existing capacity is today's capacity in `reference_year - 1`, spread over
the construction years with the shared `calculate_capacity_addition_from_cumulative` and
`format_capacity_existing` (`zen_europe/utils/utils.py`), as for all other technologies.
With `investment.use_existing_capacities: false` the industry technologies have no
existing capacity. Heat pumps, TES and DSM have no existing capacity.

## Production technologies

**Energy intensity**: glass from AIDRES (natural gas route), ceramic/paper/food from
Rehfeldt (2017), weighted by sub-process activity. Temperature mapping of fuel demand:

| Rehfeldt bin | model |
|---|---|
| < 100 °C | 0–100 °C band |
| 100–200 °C | 100–150 / 150–200 °C, split by Wolf (2017), Table 4-7 |
| > 200 °C | direct fuel input |

Rehfeldt reports final energy. Below 200 °C, the bands are heat-carrier (useful heat)
demand, so the final energy is multiplied by a reference boiler efficiency of 0.9
(`reference_boiler_efficiency` in the general assumptions); otherwise the boilers'
efficiency would be applied twice. The direct fuel input > 200 °C stays final energy.

**Fuel mix > 200 °C**: EU27 JRC-IDEES thermal final energy mix per sector, mapped via
`FUELS` (natural gas → `natural_gas`, solids → `hard_coal`, biomass and waste →
`biomass`, other liquids → `oil`). Shares below `fuel_share_cutoff` are dropped and the
rest renormalized. Other fuels (LPG, distributed steam and others) are not mapped and are
dropped before the cut-off (food: about 16 % of thermal energy).

**Costs**: JRC-EU-TIMES values (EUR2006), the ceramic proxy (EUR2014) and the food costs
are inflated to `cost.price_year` with the ECB HICP (`ECBInflation`), as all other
costs, and converted from EUR/(t/yr) to EUR/(t/h) (× 8760, rated capacity; as for all other
technologies). Variable O&M excludes energy. **Process CO2** (`carbon_intensity` in the general assumptions) covers
non-combustion emissions only.

| sector | cost source | capex | fixed O&M | var. O&M | lifetime | process CO2 (t/t) |
|---|---|---|---|---|---|---|
| glass | JRC `IGHHOLLOW01`, `IGFFLATGL01` | 2.73 M EUR/(t/h) | 208 k EUR/(t/h)/yr | 74 EUR/t | 28 yr | 0.1 |
| ceramic | Gardarsdóttir et al. (2019) clinker plant (`CementProductionGardarsdottir`) | 1.83 M EUR/(t/h) | 136 k EUR/(t/h)/yr | 7.5 EUR/t | 25 yr | 0.0642 |
| paper | JRC `IPPHIGQUA01`, `IPPLOWQUA01`, `IPPPUPCHE01`; capex override from literature | 700 EUR/(t/yr) | JRC | JRC | JRC | 0 |
| food | literature | 300 EUR/(t/yr) | 15 EUR/(t/yr)/yr | 0 | 20 yr | 0 |

The literature costs of paper and food are in
`data/raw_data/03-technology/industry/industry_production_costs.csv`
(`IndustryProductionCosts`), together with their sources.

### Glass

- Routes container/flat/fibre, weighted 60/30/10 % (AIDRES EU mix); the weights are also
  applied to Rehfeldt temperature distributions, JRC costs and kiln fuel factors.
- Fibre uses `IGFFLATGL01` (same continuous-melt furnace; no JRC fibre process).
- Process CO2 = direct emission of the AIDRES electricity route (raw-material decomposition).

### Ceramic

- Scope: demand and fuel mix come from the JRC-IDEES subsector "Ceramics & other NMM"
  (kt bricks eq.), which also includes lime, gypsum and mineral wool. `ceramic` therefore
  stands for this whole subsector: its thermal energy is roughly 1.5× that of the ceramic
  industry alone, and the fuel mix contains petcoke (other liquids) and biomass and waste
  typical of lime kilns. Energy intensity, costs, switchable share and process CO2 are based
  on ceramics data; lime process CO2 (about 0.75 t/t) is not represented.
- Rehfeldt sub-processes: tiles 5.46, technical 12.11, houseware 24.24 GJ/t.
- No ceramic cost data exist; the costs and lifetime of the cement clinker plant
  (`CementProductionGardarsdottir`, as `cement_kiln`) are used as a kiln-fired mineral proxy.
- Process CO2 from the JRC BAT share of process emissions (15 % of total): combustion
  = 8.036 GJ/t × 0.0453 t/GJ (fuel-mix weighted) ≈ 0.364 t/t; process = 0.364 × 15/85
  ≈ 0.0642 t/t.

### Paper

- Sub-processes paper, recovered fibres, chemical pulp (95.2 % of activity; weights
  56.1/28.9/15.0 %). Mechanical pulp excluded.
- Capex override: JRC (~2,283 EUR/(t/yr)) describes an integrated greenfield mill.
  Only the capex is overridden; O&M and lifetime stay JRC (integrated mill). Paper has no
  competing production route, so this only shifts the costs linearly.
  700 EUR/(t/yr) is a lower bound from brownfield conversions: Stora Enso Oulu 2026
  (~1,333), Langerbrugge 2022 (~571), Kotkamills BM2 2016 (~425–450 EUR/(t/yr)).
- Lime kiln calcination of kraft pulping is not included.
- Black liquor and bark are not modeled separately: paper's biomass boilers use the shared
  `biomass` carrier, so this internal biomass competes for the limited biomass potential,
  although in reality it is a mill by-product that is not limited this way. Industrial CHP
  electricity is not modeled.

### Food

- Rehfeldt sub-processes dairy, meat, brewing, bakery, sugar (bakery and sugar carry
  the > 200 °C demand).
- No consistent food cost data exist. Costs are rounded from three mid-sized JRC processes
  (hollow glass, quicklime, copper finishing), as food plants are mostly low-temperature
  processing lines.

## Kiln fuel switching

The > 200 °C natural gas of glass and ceramic is routed through `kiln_fuel_<sector>`,
supplied by `natural_gas_to_kiln_fuel`, `hydrogen_to_kiln_fuel` and
`electricity_to_kiln_fuel`. These model fuel choice only and have no costs: the weighted AIDRES
capex difference to the natural gas route is +1.5 EUR/t (H2) and −3.6 EUR/t (electricity).
This is optimistic (new furnace, shorter campaigns, size limits). Lifetime of the
`cement_kiln` (as `*_to_cement_fuel`). Coal, biomass and oil shares remain fixed inputs.

- **Switchable share** (`kiln_switchable_share` in the general assumptions): glass 100 %, ceramic 97.4 %; the
  remainder is a fixed `natural_gas` input.
- **Existing capacity**: `natural_gas_to_kiln_fuel` at today's kiln gas flow, with
  capacity limit (see [Diffusion](#diffusion)). Alternatives start at 0 with the
  Mannhardt `MEDIUM` diffusion rate.
- **Conversion factors** (`KILN_FUEL_INPUT`, `aidres.py`): AIDRES route fuel use
  relative to the natural gas route; for electricity, the baseline auxiliary electricity
  (already in the production technology) is subtracted. Ceramic uses the glass factors
  (no data in the ceramic BREF).

  | route (weight) | NG GJ/t | H2 GJ/t | H2/NG | elec. − baseline GJ/t | elec/NG |
  |---|---|---|---|---|---|
  | container (60 %) | 4.73 | 5.04 | 1.0655 | 5.09 − 1.07 = 4.02 | 0.8499 |
  | flat (30 %) | 5.43 | 5.78 | 1.0645 | 5.41 − 0.80 = 4.61 | 0.8490 |
  | fibre (10 %) | 7.24 | 7.17 | 0.9903 | 7.89 − 2.16 = 5.73 | 0.7914 |
  | **weighted** | | | **1.0577** | | **0.8438** |

### Ceramic switchable share

The ceramic BREF (JRC-BAT-CER-2026, §4.2.1–4.2.3) limits electrified kilns to < 1600 °C.
Tiles and houseware fire at 1000–1400 °C (fully switchable); the > 1000 °C bin of
technical ceramics is treated as not switchable (worst case).

| sub-process | fuel GJ/t | activity Mt | fuel PJ | < 1000 °C PJ | > 1000 °C PJ | not switchable PJ |
|---|---|---|---|---|---|---|
| tiles | 5.46 | 4.66 | 25.44 | 10.94 | 14.50 | – |
| technical | 12.11 | 0.68 | 8.23 | 7.00 | 1.23 | 1.23 |
| houseware | 24.24 | 0.57 | 13.82 | 4.84 | 8.98 | – |
| **total** | | | **47.49** | | | **1.23** |

Switchable = 46.26 / 47.49 ≈ 97.4 %. Limitations: the BREF gives no temperature limit for
hydrogen (§4.2.4), so the locked share is optimistic; natural gas is assumed to
follow the sector's fuel temperature distribution; coal co-firing for some facing bricks
(§4.1.6.3.5) is not included. The value is a technical ceiling: current adoption is
negligible (BREF Table 3-201: 6 electrified, 1 hydrogen of 199 plants).

## Post-combustion capture

`glass_post_comb` and `ceramic_post_comb` retrofit the production technologies analogous
to `cement_post_comb`.

- Source: DEA carbon capture catalogue, sheet "401.c Post comb - Cement kiln". Costs
  and lifetime via the technology cost database with `cement_post_comb` as proxy;
  conversion factors and capture rate are DEA 2020 values.
  `capacity_addition_unbounded` and `max_diffusion_rate` as `cement_post_comb`.
- Heat input from `natural_gas` and `hard_coal` in the sector's ratio of these fuels.
- Captured CO2 = process CO2 × 0.9 (as cement: 0.54 × 0.9 = 0.486 t/t). Combustion CO2
  is not captured, for consistency with cement.

## Heat supply

### Boilers

Six boilers per sector (biomass, natural gas, oil, electrode, coal, waste) supply the
150–200 °C band. Data from DEA "Technology Data for Industrial Process Heat" (`DEA`),
mean of lower/central/upper estimates, rebased from 2025 EUR via the technology cost
database. Costs are interpolated over 2025–2050 and held constant before 2025; variable
O&M changes via `opex_specific_variable_yearly_variation`.

| boiler | DEA sheet | capex (EUR/kW) | fixed O&M (EUR/kW/yr) | var. O&M (EUR/MWh) | lifetime | efficiency |
|---|---|---|---|---|---|---|
| electrode | 5.1a electric boiler, steam, 2 MW | 250 | 1.44 | 0.674 | 25 | 99 % |
| natural gas, oil | 6.1 boiler, gas and oil, 5 MW | 90 | 2.0 | 1.23 | 25 | 94 % |
| biomass | 6.2 boiler, biomass, 6.5 MW | 878 | 39.5 | 1.45 | 25 | 89 % |
| coal | 6.3 boiler, coal, 5 MW | 565 | 40.0 | 1.45 | 25 | 90 % |
| waste | – (as `waste_boiler_DH`) | 1,295 | 16.8 | 1.45 | 30 | 94 % |

Central values, 2025 EUR. Waste: no DEA industrial sheet; values of `waste_boiler_DH`
(capex: mean of DEA and EU Reference Scenario 2020; O&M: EU Reference Scenario 2020),
year 2025 in 2022 EUR. The 2 MW electrode boiler is used instead of 15 MW
(110 EUR/kW), which would undercut the gas boiler capex.

### Heat pumps

Per sector: three bands × two sources (waste heat, water). No existing capacity.

| | 0–100 °C | 100–150 °C | 150–200 °C |
|---|---|---|---|
| sink temperature | 75 °C | 125 °C | 175 °C |
| COP, waste heat (50 °C) | 6.96 | 2.65 | 1.79 |
| COP, water (15 °C) | 2.90 | 1.81 | 1.40 |
| capex (DEA) | 2.a, 1,200 EUR/kW | 2.b, 1,550 EUR/kW | 2.b, 1,550 EUR/kW |

- COP = 0.5 × Carnot; source temperatures from Bever (2024) and Agora (2023). Lifetime 20 yr.
- Waste-heat variants add 1,500 EUR/kW for heat recovery (`waste_heat_recovery_capex`),
  based on Stark et al. (2025), Table 2 (~1,234–1,645 EUR/kW).
- Water-source heat pumps are unlimited; waste-heat heat pumps are limited by the
  [waste heat limit](#waste-heat-limit).

### Temperature cascade

`heat_industry_temp_conversion_{150,100}_<sector>` pass heat to the next lower band
without losses or costs. Existing capacity = lower-band demand; capacity limit = demand ×
`capacity_limit_margin`. Lifetime 30 yr (`temp_cascade_lifetime`).

### Existing boiler fleet

Existing boiler capacity = sector heat demand (product demand × heat intensity) × the
sector's JRC-IDEES fuel mix in the country (EU27 for NO/UK).

- "Biomass and waste": biomass, in paper split by Eurostat `FC_IND_PPP_E`;
- CH: BFE (2025), 2023, branches 1, 3, 6 (gas 64.7 %, oil 17.7 %, biomass 8.3 %,
  waste 7.1 %, coal 2.2 %), for all sectors;
- no existing electrode boilers.

**Cut-off**: node totals below `min_boiler_capacity` are set to 0 (removes 149 of 413
non-zero entries, 0.8 % of capacity). Capacity can still be built.

## Waste heat limit

Waste-heat heat pumps use only the > 200 °C exhaust heat of their own sector at the node,
distributed over bands by heat demand:

    capacity_limit[s, band, n] = production[s, n] × fuel_intensity_>200°C[s] × heat[s, band] / Σ heat[s, :]

The limit is applied to heat pump output; the physical bound (× COP/(COP − 1)) is
1.17–2.26× larger. Totals over all nodes (GW, glass/ceramic/paper/food): 0–100 °C
0.48/6.55/0.02/0.61; 100–150 °C 1.56/1.91/0.48/0.20; 150–200 °C 3.11/3.83/0.30/0.22.

Validation against Heat Roadmap Europe (Mathiesen et al.), 2015, non-metallic minerals +
paper:

| node | model (GW) | HRE (GW) | ratio |
|---|---|---|---|
| DE | 3.24 | 3.87 | 0.84 |
| FR | 1.67 | 2.42 | 0.69 |
| HU | 0.16 | 0.26 | 0.62 |
| PL | 1.24 | 1.58 | 0.78 |
| ES | 2.00 | 2.38 | 0.84 |

## Diffusion

ZEN-garden limits capacity additions per period (`constraint_technology_diffusion_limit_total`)
to the sum of (1) own capacity × `max_diffusion_rate`, (2) 2 % of the capacity of all
technologies with the same class and reference carrier, and (3)
`capacity_addition_unbounded`. New industry heat technologies take the diffusion rate of a
proxy (`diffusion_proxy`): boilers and heat pumps that of their district heating counterpart,
alternative kiln fuels that of `hydrogen_to_cement_fuel`, post-combustion capture that of
`cement_post_comb` (all `MEDIUM` in `TechnologyDiffusionMannhardt`).

- **Heat pump seed** (`capacity_addition_unbounded`): annual `heat_pump_DH` build-out
  (fleet / `hp_seed_years`) × `interval_between_years`, split by the sector-band share of
  EU industry heat demand, by heat source and by node. Summed over nodes, all industry heat
  pumps share one DH build-out per period. Required for feasibility. `hp_seed_years` = 15
  ≈ fleet / recent DH additions (~0.15 GW/yr).
- **First-year heat pump cap** (`capacity_limit`): in the reference year, at most
  `hp_share_first_year` (2 %) of the band demand per node, split by heat source (no
  industrial heat pumps today). Without it, term (2) alone allows ~8 % of the demand.
- **Pass-through technologies** (cascade, `natural_gas_to_kiln_fuel`) share the reference
  carrier with heat pumps and alternative kiln fuels. Without capex or limit, their
  capacity would inflate term (2), so they get existing capacity and `capacity_limit` =
  flat demand × `capacity_limit_margin` (2.0, ~10 % above the max. peak-to-mean ratio of
  1.80; must be > 1).
- Heat pump market-share peers are the boilers and cascade of the same sector.

## Thermal energy storage

Per sector: water tanks (0–100, 100–150 °C) and a steam accumulator (150–200 °C). Costs
and lifetimes from Mayer et al. (2024), Table 3; self-discharge from Brown et al. (2018),
Table 1. No existing capacity.

| | water tank | steam accumulator |
|---|---|---|
| capex (EUR/kWh) | 10 | 114 |
| fixed O&M (EUR/kWh/yr) | 0.15 | 4.1 |
| variable O&M (EUR/GWh) | 1 | 1 |
| lifetime (yr) | 30 | 25 |
| energy-to-power ratio (h) | 1–24 | 0.25–4 |
| charge/discharge efficiency | 1 | 1 |
| self-discharge | 0.023 %/h (τ = 180 d) | 0.023 %/h (τ = 180 d) |

Self-discharge per hour = 1 − exp(−1/(24τ)), with τ = 180 d of central hot water tanks
(`Brown2018_Table1.csv`), also used for steam accumulators. (Dis)charging losses are
neglected; variable O&M prevents spurious cycling.

## Demand-side management

DSM is modeled as product storage (`industry_DSM.py`) for glass, ceramic, paper, food,
ammonia, clinker, methanol, primary and secondary steel, and olefin. Each product has a
shiftability category (`DSMLiteratureReview`, read from
`data/raw_data/03-technology/industry/dsm_shiftability_categories.csv`) with parameters
in `dsm_category_parameters.csv` (internal assumptions):

| category | meaning | storage and variable cost (EUR/t) | max. horizon (h) |
|---|---|---|---|
| 1 | not flexible | 1,000 | 2 |
| 2 | partially flexible | 20 | 48 |
| 3 | fully flexible | 1 | 336 |

| product | pess. | opt. | reason | sources |
|---|---|---|---|---|
| glass | 1 | 1 | continuous furnace campaigns of 5–15 yr | Hubert 2015; Hongtai 2024 |
| ceramic | 1 | 2 | tunnel kilns continuous; batch kilns can stop between cycles | Tangram |
| paper | 2 | 3 | mechanical pulping with pulp storage | Helin et al. 2017 |
| food | 1 | 2 | industry interview | Perez Recatala (ongoing) |
| methanol | 2 | 3 | power-to-methanol can ramp | Schneider & Lagoni 2023; Chen & Yang 2021 |
| primary steel | 1 | 1 | blast furnaces barely vary | Boldrini et al. 2024; Golmohamadi 2021 |
| secondary steel | 2 | 3 | EAF load flexibility | Boldrini et al. 2024; Golmohamadi 2021 |
| olefin | 1 | 2 | electrified crackers allow part load | Tiggeloven et al. 2023 |
| ammonia | 1 | 2 | flexible Haber–Bosch designs reach 10 % turndown | Salmon & Bañares-Alcántara 2023; Fahr et al. 2025 |
| clinker | 1 | 1 | "uninterruptible" | Golmohamadi 2021, Table 5 |

- Ammonia and methanol are in GW: costs per tonne are divided by the energy content
  (`Constants.AMMONIA_GWH_PER_TON`, `Constants.METHANOL_KWH_PER_KG`).
- Efficiency 0.999 (prevents simultaneous charge/discharge), self-discharge 0.
- Capacity limit = product demand per node. Lifetime 50 yr, minimum energy-to-power ratio 0.
- Ammonia and methanol are storable carriers without tank storage in the model, so their
  DSM acts mainly as cheap commodity storage rather than process flexibility.

## Carbon emissions budget

Budget per Mannhardt (2026): IPCC AR6 remaining budget, per-capita share, scaled to the
emission share of modeled sectors. With `glass`, `ceramic`, `paper` and `food`, these sectors are added to
the modeled sectors (2022 limit: ~+1.9 %).

| region | source | categories |
|---|---|---|
| EU | EEA/UNFCCC CRF (`eea_ghg_inventory.py`) | `1.A.2.d` paper, `1.A.2.e` food |
| UK glass, ceramic | DESNZ (`desnz_ghg_inventory.py`) | "Glass production", "Bricks production", "Other ceramics" |
| UK paper, food | ONS (2026) (`ons_industry_emissions.py`), only without `ammonia` and `methanol` | SIC 17; SIC 10–12 |

EU glass and ceramic combustion and process emissions are not added here. They are already
part of the `cement` budget, which takes all of `1.A.2.f` (non-metallic minerals combustion)
and `2.A` (mineral industry). The base model therefore overestimates the cement-sector
emissions: it also counts glass, ceramics, lime and other non-metallic minerals, roughly
50 Mt CO2 in 2022 for glass and ceramics alone. Hence the budget increase is only ~1.9 %.
Each UNFCCC code is counted once (`get_sector_codes`).

In the UK, the combustion of paper, food, glass and ceramics is part of the DESNZ "Other
industrial combustion", which the budget takes with the chemicals sectors (`ammonia`,
`methanol`). The ONS paper and food emissions are therefore only added if these are not
modeled. The EU budget takes all of `1.A.2.e`, although the modeled food sub-processes
cover only about 58 % of the JRC-IDEES food thermal energy (≈406 of 695 PJ), so the food
budget is slightly generous.

## References

**Data and techno-economics**
- AIDRES (2023). European Commission, DG ENER. *AIDRES: Advancing industrial decarbonization by assessing the future use of renewable energies in industrial processes.* doi:10.2833/696697. Tables 19, 21, 23.
- Brown, T., Schlachtberger, D., Kies, A., Schramm, S., Greiner, M. (2018). Synergies of sector coupling and transmission reinforcement in a cost-optimised, highly renewable European energy system. *Energy* 160, 720–739. doi:10.1016/j.energy.2018.06.222. Table 1.
- BFE (2025). Bundesamt für Energie. *Energieverbrauch in der Industrie und im Dienstleistungssektor*, Resultate 2024.
- DEA. Danish Energy Agency. *Technology Data for Industrial Process Heat*; *Technology Data for Carbon Capture, Transport and Storage*.
- Eurostat. *Complete energy balances* (nrg_bal_c). doi:10.2908/NRG_BAL_C.
- FAOSTAT. *Crops and livestock products.* <https://www.fao.org/faostat/en/#data/QCL>
- Gardarsdóttir, S. O. et al. (2019). Comparison of technologies for CO2 capture from cement production—Part 2: Cost analysis. *Energies* 12, 542.
- JRC BAT Paper (2015). *Best Available Techniques reference document for the production of pulp, paper and board.* doi:10.2791/370629.
- JRC-BAT-CER-2026. *Best Available Techniques reference document for the ceramic manufacturing industry*, final draft, April 2026.
- JRC-EU-TIMES (2019.11). Industry technologies, `JRC_EU_TIMES_model_input.xls`.
- JRC-IDEES-2023. Rózsai, M. et al. *The Integrated Database of the European Energy System.* doi:10.2760/6945021.
- Mannhardt, J. (2026). PhD dissertation, Appendix A.2.
- Mathiesen, B. V. et al. *Heat Roadmap Europe*, Ch. 2 "Waste heat potential and data for EU".
- Mayer, P. et al. (2024). Flexibility from industrial demand-side management in net-zero sector-coupled national energy systems. *Frontiers in Energy Research.* doi:10.3389/fenrg.2024.1443506.
- ONS (2026). *Atmospheric emissions: greenhouse gases by industry and gas.*
- Rehfeldt, M., Fleiter, T., Toro, F. (2017). A bottom-up estimation of the heating and cooling demand in European industry. *Energy Efficiency.* doi:10.1007/s12053-017-9571-y.
- Stark et al. (2025). Waste heat is mostly a waste of time. *Joule* 9, 102157.
- Wolf, S. (2017). *Integration von Wärmepumpen in industrielle Produktionssysteme.* PhD thesis, University of Stuttgart. Table 4-7.
- Agora Industry (2023) and Bever (2024): heat pump Carnot fraction and source temperatures.
- Fraunhofer (2012): industrial heat fuel mix by sector and temperature (comparison only).

**Demand-side management**
- Boldrini, A., Koolen, D., Crijns-Graus, W., Worrell, E., van den Broek, M. (2024). Flexibility options in a decarbonising iron and steel industry. *Renew. Sustain. Energy Rev.* 189, 113988. doi:10.1016/j.rser.2023.113988.
- Chen, C., Yang, A. (2021). Power-to-methanol: The role of process flexibility in the integration of variable renewable energy into chemical production. *Energy Convers. Manag.* 228, 113673. doi:10.1016/j.enconman.2020.113673.
- Fahr, S. et al. (2025). Dynamic simulation of a highly load-flexible Haber–Bosch plant. *Int. J. Hydrogen Energy* 102, 1231–1242. doi:10.1016/j.ijhydene.2025.01.039.
- Golmohamadi, H. (2021). Demand-side management in industrial sector: A review of heavy industries. *Renew. Sustain. Energy Rev.* 156, 111963. doi:10.1016/j.rser.2021.111963.
- Helin, K., Käki, A., Zakeri, B., Lahdelma, R., Syri, S. (2017). Economic potential of industrial demand side management in pulp and paper industry. *Energy* 141, 1681–1694. doi:10.1016/j.energy.2017.11.075.
- Hongtai (2024). Henan Hongtai Kiln Refractory Co. *Why can't the glass melting furnace be stopped?* <https://www.refractory-firebricks.com/case/343.html> (vendor page).
- Hubert, M. (2015). *Basics of industrial glass melting furnaces.* IMI-NFG course, Lecture 3. <https://www.lehigh.edu/imi/teched/GlassProcess/Lectures/Lecture03_Hubert_industglassmeltfurnaces.pdf>
- Perez Recatala, A. (ongoing). Master thesis, EPSE, ETH Zurich.
- Salmon, N., Bañares-Alcántara, R. (2023). Impact of process flexibility and imperfect forecasting on the operation and design of Haber–Bosch green ammonia. *RSC Sustainability* 1, 923–937. doi:10.1039/D3SU00067B.
- Schneider, N. T., Lagoni, Z. (2023). *Flexibility of Power-to-Methanol in 2030.* Master's thesis, Aalborg University.
- Tangram Technology. *Energy management in ceramics processing* (no date; accessed 2026-07-20). <https://tangram.co.uk/wp-content/uploads/Energy-and-Sustainability-Topics-Energy-management-in-ceramics-processing.pdf>
- Tiggeloven, J. L., Faaij, A. P. C., Kramer, G. J., Gazzani, M. (2023). Optimization of electric ethylene production: Exploring the role of cracker flexibility, batteries, and renewable energy integration. *Ind. Eng. Chem. Res.* 62(40). doi:10.1021/acs.iecr.3c02226.