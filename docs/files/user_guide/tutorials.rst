.. _tutorials.tutorials:

###########################
Tutorials
###########################

The tutorials below show how to generate and modify ZEN-europe datasets. They
build on each other, but each one can be read on its own. The underlying
procedure is described in :ref:`execution.execution`.


Prerequisites
=============

- ZEN-europe is installed (see :ref:`dev_install.dev_install`) and the
  environment is activated.
- The raw data is available. By default, ZEN-europe reads it from
  ``./data/raw_data``, relative to the folder in which the command is run.
  Another location is set with ``source_path`` in the configuration file.


Tutorial 1: Generate the default dataset
========================================

From the folder that contains ``data/raw_data``, run:

.. code-block:: shell

   zen-europe

This generates the dataset ``zen-europe`` with the default configuration file
``data/zen_europe_config.yaml`` and all default settings. The result is written
to ``./data/created_models/zen-europe``, together with
``./data/created_models/config.yaml`` for ZEN-garden.

To choose the dataset name and the output location:

.. code-block:: shell

   zen-europe --name my_dataset --output_path ./datasets

This writes ``./datasets/my_dataset`` and ``./datasets/config.yaml``.

After a run, open ``sources.md`` in any element folder, for example
``data/created_models/zen-europe/set_technologies/set_conversion_technologies/photovoltaics/sources.md``,
to see where each value comes from.


Tutorial 2: Use your own configuration file
===========================================

Instead of editing ``data/zen_europe_config.yaml``, create your own copy and
pass it to the CLI:

.. code-block:: shell

   zen-europe --config_path ./my_config.yaml

The configuration file has the following blocks:

.. code-block:: yaml

   # folder with the raw data, relative to the working directory
   source_path: "./data/raw_data"

   # settings of ZEN-garden's system file that are not controlled by a
   # setting. settings that are not listed keep ZEN-garden's defaults.
   system:
     conduct_time_series_aggregation: true
     aggregated_time_steps_per_year: 96
     use_rolling_horizon: false

   # optional: ZEN-garden's analysis and solver settings, written to
   # data/created_models/config.yaml
   analysis: {}
   solver: {}

   # ZEN-europe settings (see Tutorial 3)
   settings: {}

   # units and interpolation settings written to the energy_system folder
   energy_system:
     units:
       base_units: [hour, GW, km, megatons, megaEuro, kilotCO2, ...]
       definitions: {...}
     parameters_interpolation_off:
       parameter_name: [carbon_emissions_annual_limit]

   # optional: scenarios of system, analysis or solver settings
   # (see Tutorial 6)
   scenarios: {}

Two rules apply:

- Values that are controlled by a setting cannot be set in the ``system``
  block. For example, the nodes are set with ``region.set_nodes`` and not with
  ``system.set_nodes``, and the time horizon with ``time.*`` and not with
  ``system.reference_year``. The error message names the setting to use
  instead.
- ZEN-europe writes ``<output_path>/config.yaml``. Your configuration file must
  not be located there, since it would be overwritten.


Tutorial 3: Change settings
===========================

Settings are typed fields in categories. They are set in the ``settings:``
block of the configuration file, nested by category. Only the fields that
differ from the default need to be listed:

.. code-block:: yaml

   settings:
     time:
       last_year: 2042
       interval_between_years: 2
     region:
       set_nodes: [AT, BE, CH, DE, FR, IT, NL]
     emissions:
       use_carbon_budget: false
       use_carbon_annual_limit: true
     investment:
       use_existing_capacities: false

Each category is defined in a file in ``zen_europe/settings/``. The file lists
all fields with their type and default value:

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Category
     - Controls
   * - ``time``
     - Time horizon (``reference_year``, ``last_year``,
       ``interval_between_years``) and the year of the hourly time series
       (``time_series_year``).
   * - ``region``
     - The modeled countries (``set_nodes``).
   * - ``structure``
     - Energy system, sectors and individual elements (see Tutorial 4).
   * - ``investment``
     - Investment options: existing capacities, construction times, nuclear
       phase-out, power line limits, diffusion rates, carbon capture and
       storage expansion, and more.
   * - ``emissions``
     - Carbon budget or annual limits, temperature target and probability,
       EU ETS cap.
   * - ``cost``
     - Learning curves, nodal biomass prices, fuel price assumptions.
   * - ``availability``
     - Import caps of waste, coal, oil and biomass, and demand shedding.
   * - ``data_source``
     - Choice between alternative data sources, for example the power line
       candidates or plant-level hydro capacities.
   * - ``max_load``
     - Seasonal and nodal availability of nuclear plants.
   * - ``scenario``
     - Scenarios that are added to the dataset (see Tutorial 6).
   * - ``cache``
     - Which downloaded sources are downloaded again (see Tutorial 8).

A setting that does not exist, or a value of the wrong type, stops the run
before any data is read:

.. code-block:: text

   Unknown settings categories: ['emission']. Registered categories: [...]

In element and dataset code, the settings are available as
``self.settings.<category>.<field>``, for example
``self.settings.time.reference_year``.


Tutorial 4: Select sectors and technologies
===========================================

The ``structure`` category decides which elements are part of the dataset.

Remove sectors
--------------

.. code-block:: yaml

   settings:
     structure:
       remove_sectors: [passenger_transport, truck_transport]

A removed sector removes exactly the elements it declares.

Choose the sectors explicitly
-----------------------------

.. code-block:: yaml

   settings:
     structure:
       set_sectors: [electricity, gas, heat]

Every sector checks that its required sectors are part of ``set_sectors``.
For example, adding ``district_heating`` without ``heat`` raises:

.. code-block:: text

   Sector 'district_heating' requires sector(s) ['heat'], which are not
   included in set_sectors.

Technologies that are declared by several sectors (for example
``biomass_plant_CCS`` in ``electricity`` and ``carbon``) are only added when
all of these sectors are included.

Remove or add single elements
-----------------------------

.. code-block:: yaml

   settings:
     structure:
       remove_technologies: [nuclear, lignite_coal_plant]
       set_conversion_technologies: [photovoltaics]

``remove_technologies`` accepts technologies and carriers.
``set_conversion_technologies``, ``set_storage_technologies``,
``set_transport_technologies``, ``set_retrofitting_technologies`` and
``set_carriers`` add elements in addition to those of the sectors. Removal is
applied after all additions.

When a technology is removed, the carriers it uses may remain in the dataset
without any technology. When a carrier is removed, every technology that uses
it must be removed as well, otherwise the validation before writing fails.


.. _tutorials.models_file:

Tutorial 5: Generate several variants with a models file
========================================================

A models file declares named variants of the dataset. Each variant is a
sparse patch of the ``settings:`` block. Create ``models.yaml`` next to your
configuration file, that is ``data/models.yaml`` by default:

.. code-block:: yaml

   # optional: applied to every model
   defaults:
     settings:
       time:
         last_year: 2050

   models:
     base: {}

     no_road_transport:
       settings:
         structure:
           remove_sectors: [passenger_transport, truck_transport]

     no_road_transport_2042:
       extends: no_road_transport
       settings:
         time:
           last_year: 2042

     central_europe:
       settings:
         region:
           set_nodes: [AT, BE, CH, DE, FR, IT, LU, NL]

Generate one variant, or all of them:

.. code-block:: shell

   zen-europe --model central_europe
   zen-europe --all
   zen-europe --all --jobs 2

Each variant is written as its own dataset, named after the variant:
``data/created_models/base``, ``data/created_models/no_road_transport``, and so
on. If the models file is not next to the configuration file, pass it with
``--models_path``.

How a variant is resolved:

1. Start from the ``settings:`` block of the configuration file.
2. Merge the ``defaults``.
3. Merge the settings of the models the variant extends, furthest ancestor
   first.
4. Merge the settings of the variant itself.

Nested mappings are merged. Lists are replaced, not extended: a variant that
sets ``remove_sectors`` has to list every sector to remove, including those
set by the model it extends.

A variant may only contain ``extends`` and ``settings``. Values of the
``system`` or ``analysis`` blocks cannot be varied per model. If such a value
needs to differ between variants, it has to be turned into a setting first
(see :ref:`extending.settings`).

Use ``--sequential`` to debug a failing variant with the full log in the
current process.

Models or scenarios?
--------------------

- A **model** is a separate dataset. Use it when the variant changes what the
  dataset contains: other nodes, sectors, horizon or data sources.
- A **scenario** is a variation within one dataset, evaluated by ZEN-garden
  in its scenario analysis. Use it for sensitivities of single parameters or
  of ZEN-garden settings.

The exact distinction is not strict, and is left to the user to decide what is
more convenient. For example, a scenario that removes a sector could be
implemented as a model instead, and a scenario that changes the time horizon
could be implemented as a model instead. The main difference is that a model
is generated once and written to disk, while a scenario is evaluated by 
ZEN-garden every time it is run. 

Tutorial 6: Add scenarios to a dataset
======================================

Scenarios are written to ``scenarios.yaml`` in the dataset. ZEN-garden runs
them when its scenario analysis is enabled, which ZEN-europe does
automatically as soon as a scenario is defined.

Predefined scenarios
--------------------

The ``scenario`` settings switch on predefined sensitivities:

.. code-block:: yaml

   settings:
     scenario:
       sensitivity_demand: true
       sensitivity_discount_rate: true
       sensitivity_no_diffusion_rate: true
       run_default_scenario: true

``run_default_scenario`` does not add any scenario, but it decides whether 
the default values of the dataset are evaluated by ZEN-garden. 
If you want to run only the scenarios, set it to ``false``.


Scenarios of ZEN-garden settings
--------------------------------

Overrides of system, analysis or solver settings can be declared in the
configuration file:

.. code-block:: yaml

   scenarios:
     fine_resolution:
       system:
         aggregated_time_steps_per_year: 96
     resolution_options:
       system:
         aggregated_time_steps_per_year:
           values: [24, 96, 192]
           fmt: "tsa_{}"

A mapping with ``values`` (and optionally ``fmt``) is expanded by ZEN-garden
into one sub-scenario per value.

Scenarios of a single attribute
-------------------------------

A scenario that varies one attribute of one element is defined in the element,
where the attribute is set. For example, the discount rate sensitivity in
``EnergySystemNuts0``:

.. code-block:: python

   from zen_creator import Scenario

   def _set_discount_rate(self) -> Attribute:
       attr = self.discount_rate
       scenarios = None
       if self.settings.scenario.sensitivity_discount_rate:
           scenarios = Scenario("discount_rate", default_op=[0.0, 0.5, 1.5])
       return attr.set_data(
           default_value=0.05,
           unit="1",
           source=AssumptionInformation(description="The discount rate is 0.05."),
           scenarios=scenarios,
       )

A ``Scenario`` can replace the default value (``default_value``), the data
(``df``, ``yearly_variations_df``) or scale them (``default_op``,
``file_op``). A list of factors creates one sub-scenario per factor.

Scenarios of a whole set
------------------------

Scenarios that apply to all elements of a set, and scenarios of ZEN-garden
settings that depend on the ZEN-europe settings, are defined in
``zen_europe/global_scenarios.py``:

.. code-block:: python

   def define_global_scenarios(model: Model) -> None:
       if model.settings.scenario.sensitivity_no_diffusion_rate:
           model.scenarios.add_set(
               name="no_diffusion_rate",
               set_label="set_technologies",
               param="max_diffusion_rate",
               default_op=0.0,
           )

Scenarios of single attributes cannot be added in this function. They belong
to the element that sets the attribute.


Tutorial 7: Inspect a dataset from Python
=========================================

``create_model`` returns the model, which can be inspected before or instead
of writing it:

.. code-block:: python

   from zen_europe.model_creator import create_model

   model = create_model(config="./my_config.yaml", write=False)

   # settings and structure
   print(model.settings.time.reference_year)
   print(sorted(model.sectors))
   print(list(model.conversion_technologies))

   # values of an attribute
   capex = model.elements["photovoltaics"].capex_specific_conversion
   print(capex.default_value, capex.unit)
   print(capex.df)

   # where the values come from
   print(capex.sources_to_str())

   # generate a variant of a models file
   model = create_model(
       config="./my_config.yaml",
       models="./models.yaml",
       model_name="central_europe",
       write=False,
   )

The model can be changed before it is written. Every change needs a source or
an assumption:

.. code-block:: python

   from zen_creator import AssumptionInformation

   model.elements["nuclear"].lifetime.set_data(
       default_value=60,
       source=AssumptionInformation(description="Lifetime extended to 60 years."),
   )
   model.write()

Changes made this way are not reproducible from the configuration and models
files. For changes that are meant to stay, add a setting instead (see
:ref:`extending.settings`).


Tutorial 8: Refresh downloaded data
===================================

Some sources are downloaded from an API (for example Eurostat, ENTSO-E, the
World Bank or the ECB) and cached as files in the raw data folder. Later runs
read the cached files. To download a source again, set its flag in the
``cache`` category:

.. code-block:: yaml

   settings:
     cache:
       overwrite_eurostat: true

Reset the flag after the run, so that later runs read the new cache again.
When generating several variants with ``--all``, any active overwrite flag
makes the variants run one at a time.
