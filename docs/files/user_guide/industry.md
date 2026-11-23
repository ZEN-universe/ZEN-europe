# Industry heat sectors

*Note: this documentation page is not intended for the PR on ZEN-universe; it is
included for the completeness of the submission.*

Sectors `glass`, `ceramic`, `paper` and `food` and their shared heat supply
`industrial_heat` (`zen_europe/elements/sectors/`).
Input data are computed in `IndustryProductionData` (`industry_production_data.py`) and
`IndustryHeatSupply` (`industry_heat_supply.py`) in `zen_europe/datasets/dataset_collections/`.

## Structure

- **Sectors**: glass, ceramic, paper, food. Each has a product carrier and a
  `<sector>_production` technology. Cement, steel and chemicals are part of the main model.
  `ceramic` covers the JRC-IDEES subsector *Ceramics & other non-metallic minerals*
  (also lime, gypsum, mineral wool; see [Ceramic](#ceramic)).
- **Heat bands**: heat < 200 °C is split into `heat_industry_{0_100,100_150,150_200}`,
  so heat pump efficiency (COP) depends on the band. Heat > 200 °C is a direct fuel input
  of the production technology.
- **Shared heat supply**: the `industrial_heat` sector holds the band carriers,
  `recoverable_waste_heat`, the boilers, heat pumps and cascade. All four sectors draw on
  them, so heat is exchanged between sectors at a node. Its data cover the heat demand of
  the industry sectors in the model. The fuel of the kilns and furnaces stays per sector
  (`glass_fuel`, `ceramic_fuel`).
- **Technologies of other sectors**: `industrial_heat` also declares every technology that
  consumes or produces one of its four carriers: the production technologies of the four
  sectors, `electrolysis`, `gasification`, `anaerobic_digestion`, `biomethane_conversion`,
  `fischer_tropsch`, `haber_bosch`, `methanol_from_biomass`, `methanol_from_hydrogen`,
  `pyrolysis`, `DAC`, the post-combustion captures of cement, glass and ceramic,
  `waste_heat_integration_DH`, and the processes with [industrial waste
  heat](#industrial-waste-heat): the natural gas and hydrogen furnace fuels of glass and
  ceramic, `cement_production`, `BF_BOF`, `NG_DRI`, `H2_DRI` and `EAF`. A technology
  declared by several sectors is only added when all of them are active.
- **Default dataset**: the four sectors and `industrial_heat` are part of the default
  `structure.set_sectors` in `zen_europe/settings/structure.py`; the `zen_europe_legacy`
  model in `data/models.yaml` removes the four sectors. It cannot remove
  `industrial_heat`, which `carbon`, `hydrogen`, `ammonia`, `methanol` and `steel` require.
- **Sector links**: `industrial_heat` requires `electricity`, `gas` and `district_heating`.
  `glass` and `ceramic` require these, `industrial_heat` and `hydrogen` (kiln fuel); `paper`
  and `food` require these and `industrial_heat`. `carbon`, `hydrogen`, `ammonia`,
  `methanol`, `steel` and `cement` require `industrial_heat`, since some of their
  technologies consume or produce its carriers. `glass_post_comb` and `ceramic_post_comb` are also
  declared by `carbon` and `cement` and only added when all are active.

### General assumptions

Own numeric assumptions of the industry sectors sit in the datasets, never in the
technology or carrier modules, each with its reasoning and sources: the heat pump COP
in `Bever2024` (`bever2024.py`), the waste-heat recovery cost in `Stark2025`
(`stark2025.py`), the glass fuel shares, capex and process CO2 in
`aidres.py`, the ceramic switchable share in `rehfeldt2017.py`, the ceramic process CO2
split in `CerameUnie2021` (`cerame_unie2021.py`), the reference boiler efficiency in
`dea.py` and the capacity utilisation in `jrc_idees.py`; the fuel share cut-off in
`industry_production_data.py`; the boiler
capacity cut-off, capacity limit margin, cascade lifetime and heat pump diffusion
parameters in `industry_heat_supply.py`. The year of the
production, energy and heat statistics is `DATA_YEAR` (2023) in
`industry_production_data.py`.

### Scenarios (`data/models.yaml`, generated with `zen-europe --all`)

| scenario | change |
|---|---|
| default: four sectors | `zen_europe` |
| original ZEN-europe (no industrial heat) | `zen_europe_legacy`: removes the four sectors |
| no diffusion | `investment.use_diffusion_rates: false` |

## Product demand and existing capacity

Demand (t/h) = annual physical production ÷ 8760 h, flat over the year. Net trade is not
modeled. Existing boilers, the cascade and the kiln fuel are all based on this demand. Existing production capacity (t/h) = installed capacity ÷ 8760 h
where JRC-IDEES reports it (glass, paper: about 26–29 % headroom above demand) and demand ÷
the capacity utilisation (0.783, the mean EU27 output / capacity of glass and paper,
`get_industry_capacity_utilisation`) otherwise.

| sector | demand basis | existing capacity basis |
|---|---|---|
| glass, paper | JRC-IDEES-2023 physical output | JRC-IDEES-2023 installed capacity |
| ceramic | JRC-IDEES thermal final energy ÷ Rehfeldt weighted fuel intensity | demand ÷ 0.783 |
| food | Rehfeldt EU28+3 activity per sub-process, distributed to nodes by FAOSTAT production of a proxy item (`FOOD_ITEMS`) | demand ÷ 0.783 |

**Nodes without JRC-IDEES** (CH, NO, UK; `NODES_WITHOUT_IDEES`):

- glass, ceramic: CH = AT, NO = FI, UK = DE × population UK/DE in `DATA_YEAR`
  (World Bank, `WorldBankPopulation`);
- paper: 2008 *consumption* from JRC BAT Paper (2015), Table 1.2 (CH 1,397, NO 831,
  UK 11,443 kt), used as demand; existing capacity = demand ÷ 0.783. No existing boilers at these nodes;
- food: FAOSTAT covers all nodes.

**Vintages**: existing capacity is today's capacity in `reference_year - 1`, spread over
the construction years with the shared `calculate_capacity_addition_from_cumulative` and
`format_capacity_existing` (`zen_europe/utils/utils.py`), as for all other technologies.
With `investment.use_existing_capacities: false` the industry technologies have no
existing capacity. Heat pumps have no existing capacity.

## Production technologies

**Energy intensity**: glass from AIDRES (natural gas route), ceramic/paper/food from
Rehfeldt (2017), weighted by sub-process activity. Temperature mapping of fuel demand:

| Rehfeldt bin | model |
|---|---|
| < 100 °C | 0–100 °C band |
| 100–200 °C | 100–150 / 150–200 °C, split by Wolf (2017), Table 4-7 |
| > 200 °C | direct fuel input |

Rehfeldt reports final energy. Below 200 °C, the bands are heat-carrier (useful heat)
demand, so the final energy is multiplied by a reference boiler efficiency of 0.93, the
mean of the DEA industrial boilers (electrode 0.99, gas/oil 0.94, coal 0.90, biomass 0.89;
`get_mean_efficiency_industry_boilers`); otherwise the boilers'
efficiency would be applied twice. The direct fuel input > 200 °C stays final energy.

**Fuel mix > 200 °C**: EU27 JRC-IDEES thermal final energy mix per sector, mapped via
`FUELS` (natural gas → `natural_gas`, solids → `hard_coal`, biomass and waste →
`biomass`, other liquids → `oil`). Shares below `FUEL_SHARE_CUTOFF` are dropped and the
rest renormalized. Other fuels (LPG, distributed steam and others) are not mapped and are
dropped before the cut-off (food: about 16 % of thermal energy).

**Costs**: none (capex, fixed and variable O&M are 0, `get_no_cost`). Each product has
a single production technology and a fixed, flat demand, without trade or demand
shedding, so the production and capacity follow the demand and the costs would only add
a constant to the objective. Fuel switching and capture are separate retrofits with
their own costs, so the costs of the production technologies do not affect them either.
This no longer holds once a product gets a competing route, trade or demand shedding.
**Lifetime** from JRC-EU-TIMES (`get_lifetime`), which only sets the vintages of the
existing capacity. **Process CO2** covers non-combustion emissions only.

| sector | lifetime source | lifetime | process CO2 (t/t) |
|---|---|---|---|
| glass | JRC `IGHHOLLOW01`, `IGFFLATGL01`, weighted by route | 28 yr | 0.121 |
| ceramic | JRC `INMPRCGAS01` (gas process heat, non-metallic minerals; no ceramic process) | 30 yr | 0.120 |
| paper | JRC `IPPHIGQUA01`, `IPPLOWQUA01`, `IPPPUPCHE01`, weighted by activity | 25 yr | 0 |
| food | JRC `IOIPRCGAS01` (gas process heat, other industries; no food process) | 30 yr | 0 |

### Glass

- Routes container/flat/fibre, weighted 60/30/10 % (AIDRES EU mix); the weights are also
  applied to Rehfeldt temperature distributions, JRC lifetimes and kiln fuel factors.
- Fibre uses `IGFFLATGL01` (same continuous-melt furnace; no JRC fibre process).
- Process CO2 = direct emission of the AIDRES electricity routes (raw-material
  decomposition), weighted by production share: 0.6 × 0.073 + 0.3 × 0.182 + 0.1 × 0.227
  = 0.121 t/t.

### Ceramic

- Scope: demand and fuel mix come from the JRC-IDEES subsector "Ceramics & other NMM"
  (kt bricks eq.), which also includes lime, gypsum and mineral wool. `ceramic` therefore
  stands for this whole subsector: its thermal energy is roughly 1.5× that of the ceramic
  industry alone, and the fuel mix contains petcoke (other liquids) and biomass and waste
  typical of lime kilns. Energy intensity, switchable share and process CO2 are based
  on ceramics data; lime process CO2 (about 0.75 t/t) is not represented.
- Rehfeldt sub-processes: tiles 5.46, technical 12.11, houseware 24.24 GJ/t.
- Ceramic kilns are fired with natural gas today; the JRC-IDEES biomass, oil and coal of
  the subsector are not modeled.
- Process CO2 from the emission split of the European ceramic industry in 2020
  (Cerame-Unie (2021), Ceramic Roadmap to 2050, p. 30: 64 % fuel combustion, 19 %
  indirect, 17 % process): combustion = 8.036 GJ/t × 0.0561 t/GJ (natural gas, IPCC)
  = 0.451 t/t; process = 0.451 × 17/64 = 0.120 t/t.

### Paper

- Sub-processes paper, recovered fibres, chemical pulp (95.2 % of activity; weights
  56.1/28.9/15.0 %). Mechanical pulp excluded.
- Lime kiln calcination of kraft pulping is not included.
- Black liquor and bark are not modeled separately: paper's biomass boilers use the shared
  `biomass` carrier, so this internal biomass competes for the limited biomass potential,
  although in reality it is a mill by-product that is not limited this way. Industrial CHP
  electricity is not modeled.

### Food

- Rehfeldt sub-processes dairy, meat, brewing, bakery, sugar (bakery and sugar carry
  the > 200 °C demand).

## Kiln fuel switching

### Glass

Glass furnaces are fired with natural gas, the AIDRES reference route; the JRC-IDEES
solids and other fuels of glass are not modeled. The > 200 °C fuel of `glass_production`
is `glass_fuel`, supplied by the retrofits `natural_gas_to_glass_fuel`,
`hydrogen_to_glass_fuel` and `electricity_to_glass_fuel` of `glass_production`, as the
`*_to_cement_fuel` retrofits of `cement_production`. The base electricity of the furnace
(AIDRES, independent of the fuel) stays an input of `glass_production`.

- **Maximum share** (`GLASS_FUEL_MAX_SHARE`, `aidres.py`): AIDRES has full natural gas,
  hydrogen and electric routes, so each retrofit can cover 100 % of the glass fuel. The
  retrofit flow coupling factor is the maximum share times the glass fuel per tonne.
- **Costs**: none; the weighted AIDRES capex difference to the natural gas route is
  +1.5 EUR/t (H2) and −3.6 EUR/t (electricity). This is optimistic (new furnace, shorter
  campaigns, size limits). Lifetime of `glass_production`.
- **Existing capacity**: `natural_gas_to_glass_fuel` at today's glass fuel demand, with
  capacity limit (see [Diffusion](#diffusion)). Hydrogen and electricity start at 0 with
  the diffusion rate of `hydrogen_to_cement_fuel`.

### Ceramic

Ceramic kilns are fired with natural gas. The > 200 °C fuel of `ceramic_production` is
`ceramic_fuel`, supplied by the retrofits `natural_gas_to_ceramic_fuel`,
`hydrogen_to_ceramic_fuel` and `electricity_to_ceramic_fuel` of `ceramic_production`, as
for glass.

- **Maximum share**: natural gas, today's fuel, 100 %; hydrogen and electricity each the
  switchable share of 97.40 % (`get_switchable_share_ceramic`, Rehfeldt; see
  [Ceramic switchable share](#ceramic-switchable-share)), so the > 1000 °C fuel of
  technical ceramics stays natural gas. The switchable share is derived for electrified
  kilns and is a proxy for hydrogen.
- **Conversion factors**: as the glass routes (see [Conversion factors](#conversion-factors)).
- **Costs**: none, as glass. Lifetime of `ceramic_production`.
- **Existing capacity**: `natural_gas_to_ceramic_fuel` at today's ceramic fuel demand,
  with capacity limit (see [Diffusion](#diffusion)). Hydrogen and electricity start at 0
  with the diffusion rate of `hydrogen_to_cement_fuel`.

### Conversion factors

`KILN_FUEL_INPUT` (`aidres.py`): AIDRES route fuel use relative to the natural gas route;
for electricity, the baseline auxiliary electricity (already in the production
technology) is subtracted. Ceramic uses the glass factors (no data in the ceramic BREF).

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

Switchable = 1 − (12.11 × 0.68 × 0.15) / Σ (fuel × activity) = 1 − 1.235 / 47.495 =
97.40 %. Limitations: the BREF gives no temperature limit for
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

Six boilers (`<fuel>_boiler_industry`: biomass, natural gas, oil, electrode, coal, waste)
supply the 150–200 °C band. Data from DEA "Technology Data for Industrial Process Heat" (`DEA`),
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

Three bands × two sources (waste heat, water), `heat_pump_industry_<band>_<source>`. No
existing capacity.

| | 0–100 °C | 100–150 °C | 150–200 °C |
|---|---|---|---|
| sink temperature | 75 °C | 125 °C | 175 °C |
| COP, waste heat (50 °C) | 6.96 | 2.65 | 1.79 |
| COP, water (15 °C) | 2.90 | 1.81 | 1.40 |
| waste heat per heat (1 − 1/COP) | 0.856 | 0.623 | 0.441 |
| capex (DEA) | 2.a, 1,200 EUR/kW | 2.b, 1,550 EUR/kW | 2.b, 1,550 EUR/kW |
| waste heat recovery (Stark) | 1,355 EUR/kW | 986 EUR/kW | 699 EUR/kW |

- COP = 0.5 × Carnot; source temperatures from Bever (2024) and Agora (2023). Lifetime 20 yr.
- Waste-heat variants take electricity (1/COP) and `recoverable_waste_heat` (1 − 1/COP)
  per heat output (`get_conversion_factor_heat_pump_waste_heat`), so the waste heat they
  use is bounded by the carrier balance at the node, see [Industrial waste
  heat](#industrial-waste-heat). They have no capacity limit.
- Waste-heat variants add the heat recovery of Stark et al. (2025), 1,788 USD/kWth
  (2025 USD), converted with the ECB exchange rate of 2025 and inflated to the price
  year (~1,583 EUR/kW in 2025 EUR). It is per kW of recovered waste heat, so it is
  multiplied by the waste heat per heat output (1 − 1/COP); the values in the table
  are per kW of heat output, 2025 EUR.
- Water-source heat pumps have no capacity limit.

### Temperature cascade

`heat_industry_temp_conversion_{150,100}` pass heat to the next lower band
without losses or costs. Existing capacity = lower-band demand; capacity limit = demand ×
`CAPACITY_LIMIT_MARGIN`. Lifetime 30 yr (assumed).

`heat_industry_temp_conversion_rwh` ends the cascade: it passes 0–100 °C heat to
`recoverable_waste_heat` without losses or costs. No existing capacity and no capacity
limit, since no technology with a diffusion rate shares its reference carrier.
`recoverable_waste_heat` is used by the waste-heat heat pumps (see [Heat
pumps](#heat-pumps)), fed into district heating (see [District heat
integration](#district-heat-integration)) or exported (blown off) without limit. Other technologies, e.g. `electrolysis` and the processes with [industrial waste
heat](#industrial-waste-heat), also output `recoverable_waste_heat`.

### Industrial waste heat

The industrial processes output the recoverable waste heat of their exhaust, cooled to
55 °C (sEEnergies D5.1, Fleiter et al. 2020, `SeenergiesIndustrialWasteHeat`), as a
share of their energy input or, for steel, per tonne (`IndustrialWasteHeat` in
`industrial_waste_heat.py`). `settings.operation.use_industrial_waste_heat` (default
`true`) switches it off.

| technologies | waste heat | of | sEEnergies process |
|---|---|---|---|
| `natural_gas_to_glass_fuel`, `hydrogen_to_glass_fuel` | 11 % | fuel input | regenerative furnace: without minus with batch/cullet preheating |
| `natural_gas_to_ceramic_fuel`, `hydrogen_to_ceramic_fuel` | 11 % | fuel input | as glass (proxy) |
| `cement_production` | 17 % | `cement_fuel` | dry kiln with preheater (3.7 GJ/t clinker, as the model's kiln) |
| `paper_production` | 1 % | total input | board & packaging paper: boilers without minus with heat recovery |
| `food_production` | 1 % | total input | as paper (proxy) |
| `BF_BOF` | 0.624 GJ/t | steel | blast stove exhaust: 10 % of 1.5 GJ/t without minus 4 % of 1.4 GJ/t with heat recovery; plus BOF off-gases: 0.55 GJ/t without minus 0.02 GJ/t with heat recovery; no coke ovens |
| `EAF` | 0.201 GJ/t | steel | EAF: 12 % of 1.8 GJ/t without minus 1 % of 1.5 GJ/t with scrap preheating |
| `NG_DRI`, `H2_DRI` | 0.201 GJ/t | steel | as EAF (proxy; no DRI data) |

sEEnergies gives the steel shares per fuel of the blast stove or the EAF alone, not per
input of the whole route, so the steel waste heat is not scaled by the Agora input.

Electric furnaces and kilns (`electricity_to_glass_fuel`, `electricity_to_ceramic_fuel`)
have no exhaust and output no waste heat.

The DEA heat output of `cement_post_comb` (1.65 MWh/tCO2) includes the pre-cooling of the
kiln flue gas and the kiln waste heat recovery units (DEA 401.c, notes A, I, M). The kiln
exhaust heat that `cement_production` outputs is therefore subtracted per captured CO2:
17 % × 3.7 GJ/t clinker ÷ (0.54 tCO2/t clinker × 0.9 capture rate) = 0.36 MWh/tCO2,
so 1.29 MWh/tCO2 remain. Without industrial waste heat, the full 1.65 MWh/tCO2 is kept.
`glass_post_comb` and `ceramic_post_comb` keep the full 1.65 MWh/tCO2: they capture only
the process CO2, and the furnace exhaust depends on the glass or ceramic fuel technology
(none for electric furnaces).

### District heat integration

`waste_heat_integration_DH` (sectors `industrial_heat` and `district_heating`) feeds
`recoverable_waste_heat` into `district_heat` without losses. Capex: the waste-heat
recovery of Stark et al. (2025) per kW of recovered heat, as for the waste-heat heat pumps
(here one kW of district heat is one kW of recovered heat); no O&M. Lifetime of `district_heating_grid`, diffusion rate of
`heat_pump_DH`; no existing capacity.

### Existing boiler fleet

Existing boiler capacity = Σ over sectors of the sector heat demand (product demand × heat
intensity) × the sector's JRC-IDEES fuel mix in the country (EU27 for NO/UK).

- "Biomass and waste": biomass, in paper split by Eurostat `FC_IND_PPP_E`;
- CH: BFE (2025), 2023, branches 1, 3, 6 (gas 64.7 %, oil 17.7 %, biomass 8.3 %,
  waste 7.1 %, coal 2.2 %), for all sectors;
- no existing electrode boilers.

**Cut-off**: node totals (summed over the sectors) below `MIN_BOILER_CAPACITY` (0.005 GW) are set to
0. Capacity can still be built.

## Diffusion

ZEN-garden limits capacity additions per period (`constraint_technology_diffusion_limit_total`)
to the sum of (1) own capacity × `max_diffusion_rate`, (2) 2 % of the capacity of all
technologies with the same class and reference carrier, and (3)
`capacity_addition_unbounded`. New industry heat technologies take the diffusion rate of a
proxy (`diffusion_proxy`): boilers and heat pumps that of their district heating counterpart,
alternative kiln fuels that of `hydrogen_to_cement_fuel`, post-combustion capture that of
`cement_post_comb` (all `MEDIUM` in `TechnologyDiffusionMannhardt`).

- **Heat pump seed** (`capacity_addition_unbounded`): annual `heat_pump_DH` build-out
  (fleet / `HP_SEED_YEARS`) × `interval_between_years`, split by the band share of
  EU industry heat demand, by heat source and by node. Summed over nodes, all industry heat
  pumps share one DH build-out per period. Required for feasibility. `HP_SEED_YEARS` = 15
  ≈ fleet / recent DH additions (~0.15 GW/yr).
- **Pass-through technologies** (cascade, `natural_gas_to_glass_fuel`,
  `natural_gas_to_ceramic_fuel`) share the reference
  carrier with heat pumps and alternative kiln fuels. Without capex or limit, their
  capacity would inflate term (2), so they get existing capacity and `capacity_limit` =
  flat demand × `CAPACITY_LIMIT_MARGIN` (2.0, ~10 % above the max. peak-to-mean ratio of
  1.80; must be > 1).
- Heat pump market-share peers are the boilers and cascade of the same band.

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

- AIDRES (2023). European Commission, DG ENER. *AIDRES: Advancing industrial decarbonization by assessing the future use of renewable energies in industrial processes.* doi:10.2833/696697. Tables 19, 21, 23.
- BFE (2025). Bundesamt für Energie. *Energieverbrauch in der Industrie und im Dienstleistungssektor*, Resultate 2024.
- DEA. Danish Energy Agency. *Technology Data for Industrial Process Heat*; *Technology Data for Carbon Capture, Transport and Storage*.
- Eurostat. *Complete energy balances* (nrg_bal_c). doi:10.2908/NRG_BAL_C.
- FAOSTAT. *Crops and livestock products.* <https://www.fao.org/faostat/en/#data/QCL>
- JRC BAT Paper (2015). *Best Available Techniques reference document for the production of pulp, paper and board.* doi:10.2791/370629.
- JRC-BAT-CER-2026. *Best Available Techniques reference document for the ceramic manufacturing industry*, final draft, April 2026.
- JRC-EU-TIMES (2019.11). Industry technologies, `JRC_EU_TIMES_model_input.xls`.
- JRC-IDEES-2023. Rózsai, M. et al. *The Integrated Database of the European Energy System.* doi:10.2760/6945021.
- Mannhardt, J. (2026). PhD dissertation, Appendix A.2.
- ONS (2026). *Atmospheric emissions: greenhouse gases by industry and gas.*
- Rehfeldt, M., Fleiter, T., Toro, F. (2017). A bottom-up estimation of the heating and cooling demand in European industry. *Energy Efficiency.* doi:10.1007/s12053-017-9571-y.
- Stark et al. (2025). Waste heat is mostly a waste of time. *Joule* 9, 102157.
- Wolf, S. (2017). *Integration von Wärmepumpen in industrielle Produktionssysteme.* PhD thesis, University of Stuttgart. Table 4-7.
- Agora Industry (2023) and Bever (2024): heat pump Carnot fraction and source temperatures.
- Fraunhofer (2012): industrial heat fuel mix by sector and temperature (comparison only).
