.. _extending.extending:

#########################################
Adding Elements, Datasets and Settings
#########################################

This page lists the rules for extending ZEN-europe. They keep the code base
readable for everybody who works on it: every value can be traced from the
element to the data source, and every data source is processed in exactly one
place.

The base classes (``Model``, ``Element``, ``Attribute``, ``Dataset``,
``DatasetCollection``, ...) belong to ZEN-creator and are described in its
`API reference <https://zen-creator.readthedocs.io/en/latest/files/api/model.html>`_.
How to add a new attribute to these base classes is described in the
`ZEN-creator developer guide
<https://zen-creator.readthedocs.io/en/latest/files/developer_guide/add_new_params.html>`_.


Layers
======

Data flows through four layers. Each layer has one responsibility.

.. mermaid::

   flowchart LR
       R[Raw data files<br/>or API] --> D[Dataset<br/>one source]
       D --> C[DatasetCollection<br/>several sources]
       D --> E[Element<br/>_set_attribute]
       C --> E
       E --> O[ZEN-garden<br/>input folder]

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Layer
     - Responsibility
     - Location
   * - Dataset
     - Read, clean and convert one data source. Provide
       ``get_<attribute>()`` methods.
     - ``zen_europe/datasets/datasets/<category>/``
   * - DatasetCollection
     - Combine several datasets into one attribute (selection, fallback,
       averaging, corrections).
     - ``zen_europe/datasets/dataset_collections/``
   * - Element
     - Decide for each attribute which dataset, collection or assumption it
       uses. No data processing.
     - ``zen_europe/elements/<element type>/``
   * - Settings
     - Every choice that changes the generated dataset.
     - ``zen_europe/settings/``


Rules for datasets
==================

1. One source, one dataset
--------------------------

Every source (publication, database, API) gets its own ``Dataset`` subclass
in its own file. 

- Place the file in the category that matches the content of the source:
  ``energy_system``, ``carrier``, ``technology`` or ``financial``.
- Name the file and the class after the source, for example
  ``irena_solar_capacity.py`` with ``class IRENASolarCapacity``.
- Set a unique ``name`` in snake case, for example
  ``name = "irena_solar_capacity"``.
- Store the raw files in the matching folder of the raw data:
  ``01-energy_system``, ``02-carrier``, ``03-technology`` or ``04-monetary``.

2. Cite the source
------------------

``_set_metadata()`` returns a complete ``MetaData`` object: title, authors,
publication, year, and a URL or DOI. Use ``note`` for anything a reader needs
to know about the source or the part of the source that is used.

3. Load and clean in the dataset
--------------------------------

- ``_set_path()`` builds the path from ``self.source_path``.
- ``_set_data()`` reads the files and returns a ``DataFrame``, a ``Series`` or
  a dict of them.
- Convert the data to the conventions of the model here: country codes as
  NUTS0 codes (see ``zen_europe/utils/utils.py``), ZEN-europe technology and
  carrier names, integer years, and consistent units.

4. Expose attributes through ``get_<attribute>()``
--------------------------------------------------

Elements only call public ``get_<attribute>(element)`` methods. They return an
``Attribute`` that carries the source:

.. code-block:: python

   def get_capacity_existing(self, element: Element) -> Attribute:
       """Existing capacity of the technology."""
       data = self._capacity_additions(element)
       return element.capacity_existing.set_data(
           df=data,
           unit="GW",
           source=SourceInformation(
               description="Capacity additions derived from cumulative capacity.",
               metadata=self.metadata,
           ),
       )

Helper methods start with an underscore. A dataset may also expose methods
that return plain data (for example ``get_population()``) for use by a
collection.

5. Cache downloaded sources
---------------------------

A source that is downloaded from an API is stored as a file in the raw data
folder and read from there in later runs. Add an ``overwrite_<dataset>`` flag
to ``CacheSettings`` in ``zen_europe/settings/cache.py`` and check it before
reading the cache:

.. code-block:: python

   from zen_europe.settings.cache import get_active_cache_settings

   def _set_data(self) -> pd.DataFrame:
       cache_path = self.path / self.CACHE_FILE
       overwrite = get_active_cache_settings().overwrite_my_source
       if cache_path.exists() and not overwrite:
           return pd.read_csv(cache_path, index_col=0)
       data = self._download()
       data.to_csv(cache_path)
       return data

6. Keep in mind that datasets are singletons
--------------------------------------------

A dataset is constructed on its first call and reused for the rest of the
process. The arguments of the first call (source path, settings, nodes) are
the ones that are used. 

Rules for dataset collections
=============================

1. Combine sources in a collection
----------------------------------

When an attribute uses more than one source, create a ``DatasetCollection``
in ``zen_europe/datasets/dataset_collections/``. Name it after the attribute
or topic it provides, for example ``electricity_demand``,
``lifetime_expectation`` or ``technology_cost_database``.

2. List the sources in ``_get_data()``
--------------------------------------

``_get_data()`` returns a dict of the datasets (or other collections) the
collection uses:

.. code-block:: python

   def _get_data(self) -> dict[str, Dataset]:
       return {
           "tech_db": TechnologyCostDatabase(self.settings, self.source_path),
           "powerplantmatching": PowerPlantMatching(self.source_path),
       }

The metadata of the collection is built from these entries, including nested
collections, so the citations of all sources end up in ``sources.md``.

3. Only combine
---------------

The ``get_<attribute>()`` methods of a collection select, fall back, average
or correct values of its datasets. Reading and cleaning a single source stays
in the dataset. The description of the returned source explains how the
sources are combined, and the metadata is ``self.metadata``.

4. Use common schemas for similar sources
-----------------------------------------

When several sources report the same kind of data, let every dataset return
the same format so that the collection can combine them without
source-specific code. The technology cost datasets (DEA, TYNDP, DIW, LUW,
EUREF, ...) all follow ``financial/_cost_schema.py`` and are combined by
``TechnologyCostDatabase``. A new cost source only needs a new dataset in this
format and an entry in the collection.


Rules for elements
==================

1. One element, one class
-------------------------

Each carrier and technology is a subclass of the matching ZEN-creator class
in its own file:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Base class
     - Folder
   * - ``Carrier``
     - ``elements/carriers/``
   * - ``ConversionTechnology``
     - ``elements/conversion_technologies/``
   * - ``RetrofittingTechnology``
     - ``elements/retrofitting_technologies/``
   * - ``StorageTechnology``
     - ``elements/storage_technologies/``
   * - ``TransportTechnology``
     - ``elements/transport_technologies/``

The ``name`` of the class is the name of the element in ZEN-garden and must be
unique. The ZEN-creator templates (``aa_template.py`` in each element folder
of ZEN-creator) are a starting point.

2. Implement the required methods
---------------------------------
Some attributes are required by ZEN-garden and must be set in every element.
The following methods are required for every element type:

- every technology: ``_set_reference_carrier`` and ``_set_lifetime``
- conversion technologies: ``_set_input_carrier``, ``_set_output_carrier``
  and ``_set_conversion_factor``
- retrofitting technologies: ``_set_retrofit_flow_coupling_factor`` and
  ``_set_retrofit_reference_carrier``

Every other attribute keeps the ZEN-creator default unless a
``_set_<attribute>()`` method is implemented.

3. Do not read or transform data in the element
-----------------------------------------------

A ``_set_<attribute>()`` method either calls a dataset or collection, or sets
an explicit assumption. It does not read or transform raw data:

.. code-block:: python

   def _set_capacity_existing(self) -> Attribute:
       """Existing capacity of photovoltaics."""
       if self.settings.investment.use_existing_capacities:
           return IRENASolarCapacity(source_path=self.source_path).get_capacity_existing(self)
       return self.capacity_existing.set_data(
           default_value=0,
           source=AssumptionInformation(description="No existing capacities."),
       )

Use ``SourceInformation`` for values from a source and
``AssumptionInformation`` for modeling choices. An attribute may read other
attributes, also of other elements. They are built on demand.

4. Register the element
-----------------------

- Import the class in the ``__init__.py`` of its folder.
- Add the class to the ``elements`` list of every sector it belongs to. A
  technology that links two sectors (for example a CCS retrofit of a power
  plant) is listed in both and is only added when both are included.
- Every carrier used by the technology must be part of the model, usually by
  being listed in the same sector or in one of its required sectors.

5. Define attribute scenarios in the element
--------------------------------------------

A scenario that varies a single attribute belongs in the
``_set_<attribute>()`` method of that attribute, switched on by a ``scenario``
setting. It is not defined in ``global_scenarios.py``, which only takes
scenarios of ZEN-garden settings and of whole element sets. See
:ref:`extending.scenarios`.


Adding a sector
===============

1. Create ``zen_europe/elements/sectors/<sector>.py`` with a ``Sector``
   subclass, a unique ``name``, the ``required_sectors`` and the list of
   ``elements``.
2. Import it in ``zen_europe/elements/sectors/__init__.py``.
3. If the sector is part of the default dataset, add it to the default of
   ``set_sectors`` in ``zen_europe/settings/structure.py``.


.. _extending.settings:

Adding a setting
================

Every choice that changes the generated dataset is a setting and can
be varied in ``models.yaml``.

Add a field to an existing category
-----------------------------------

Add a typed field with a default value to the matching class in
``zen_europe/settings/``:

.. code-block:: python

   class InvestmentSettings(SettingsCategory):
       name: ClassVar[str] = "investment"

       use_my_new_option: bool = False

Read it where it is needed as ``self.settings.investment.use_my_new_option``
(elements) or through the ``settings`` passed to a dataset or collection.

Add a new category
------------------

1. Create ``zen_europe/settings/<category>.py`` with a ``SettingsCategory``
   subclass and a unique ``name``.
2. Import it in ``zen_europe/settings/__init__.py``. The category is then
   available as ``model.settings.<name>`` and in the ``settings:`` block.

Control a ZEN-garden configuration value
----------------------------------------

If a setting determines a value of the ZEN-garden configuration, declare it
in ``controls``. The setting is then the only place where the value can be
set, and the configuration file rejects it:

.. code-block:: python

   class RegionSettings(SettingsCategory):
       name: ClassVar[str] = "region"
       controls: ClassVar[dict[str, str]] = {"set_nodes": "system.set_nodes"}

       set_nodes: list[str] = Field(default_factory=lambda: ["AT", "BE", ...])

For values that are derived from several fields, override ``apply(config)``,
as ``TimeSettings`` does for ``optimized_years``.


.. _extending.scenarios:

Adding a scenario
=================

A scenario varies values inside one dataset, so that ZEN-garden solves several
variations of it in one scenario analysis. 

All entries are collected in ``model.scenarios`` and written to
``scenarios.yaml``. The scenario analysis of ZEN-garden is switched on
automatically as soon as one scenario is defined. Whether the unmodified
dataset is solved as well is controlled by ``scenario.run_default_scenario``.

Where a scenario is defined
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 34 33 33

   * - What varies
     - Where it is defined
     - How
   * - One attribute of one element
     - In the element, in the ``_set_<attribute>()`` method of that attribute
     - ``set_data(scenarios=...)`` or ``attr.add_scenarios(...)``
   * - One attribute of a whole set
     - ``zen_europe/global_scenarios.py``
     - ``model.scenarios.add_set()``
   * - System, analysis or solver settings
     - ``zen_europe/global_scenarios.py``, or the configuration file
     - ``model.scenarios.add()``, or the ``scenarios:`` block

Attribute scenarios cannot be registered from ``global_scenarios.py``: the
registry raises an error that names the attribute to define them on instead.
This keeps a variation next to the value it varies.

What a scenario changes
-----------------------

A ``Scenario`` needs a name and at least one entry type:

.. list-table::
   :header-rows: 1
   :widths: 32 38 30

   * - Entry type
     - Effect
     - Written to
   * - ``default_value`` (with ``unit``)
     - Replaces the default value
     - ``attributes_<suffix>.yaml``
   * - ``df``
     - Replaces the time series or node, edge and year values
     - ``<attribute>_<suffix>.csv``
   * - ``yearly_variations_df``
     - Replaces the yearly variations
     - ``<attribute>_yearly_variation_<suffix>.csv``
   * - ``default_op``
     - Factor on the default value
     - ``scenarios.yaml`` only
   * - ``file_op``
     - Factor on the data
     - ``scenarios.yaml`` only

A list as ``default_op`` or ``file_op`` creates one sub-scenario per factor,
so a whole sensitivity range fits in one entry. The values of a scenario are
validated with the same rules as the values of the attribute itself.

The ``name`` groups entries across attributes and elements into one scenario:
several elements that use the same name are varied together. The ``suffix``
names the generated files and defaults to the name, which is why the shared
sensitivities below use a short suffix such as ``low`` with longer names.

Always gate a scenario behind a setting
---------------------------------------

Add a flag to ``ScenarioSettings`` in ``zen_europe/settings/scenario.py``, so
that the default dataset stays free of scenarios and the sensitivity can be
switched on per model in ``models.yaml``:

.. code-block:: python

   class ScenarioSettings(SettingsCategory):
       """Scenario settings."""

       name: ClassVar[str] = "scenario"

       sensitivity_my_parameter: bool = False

Pattern 1: scale or replace an assumption
-----------------------------------------

When the element sets the value itself, pass the scenarios to ``set_data()``.
``EnergySystemNuts0`` varies the discount rate this way, with one sub-scenario
per factor:

.. code-block:: python

   def _set_discount_rate(self) -> Attribute:
       """Sets the discount rate of the energy system."""
       attr = self.discount_rate
       scenarios = None
       if self.settings.scenario.sensitivity_discount_rate:
           scenarios = Scenario("discount_rate", default_op=[0.0, 0.5, 1.5])
       return attr.set_data(
           default_value=0.05,
           unit="1",
           source=AssumptionInformation(
               description="The discount rate is set to 0.05.",
           ),
           scenarios=scenarios,
       )

Passing ``scenarios=None`` when the setting is off keeps the method to a
single ``set_data()`` call.

Pattern 2: scale data that a dataset produced
---------------------------------------------

When the value comes from a dataset, add the scenarios to the attribute the
dataset returned. The demand carriers do this with a factor on the time
series:

.. code-block:: python

   def _set_demand(self) -> Attribute:
       """Return the demand for electricity."""
       electricity_demand_dataset = ElectricityDemand(
           self.settings, self.model.config.system.set_nodes, self.source_path
       )
       attr = electricity_demand_dataset.get_demand(self)
       if self.settings.scenario.sensitivity_demand:
           attr.add_scenarios(demand_sensitivity_scenarios(self.name))
       return attr

``zen_europe/utils/demand_sensitivity.py`` groups the demand carriers into
economic sectors and returns the two scenarios of the sector a carrier belongs
to, so that all carriers of a sector vary together:

.. code-block:: python

   def demand_sensitivity_scenarios(carrier_name: str) -> list[Scenario]:
       """Return the low and high demand scenarios of a carrier's sector."""
       sector = _CARRIER_SECTORS[carrier_name]
       return [
           Scenario(f"{sector}_low", suffix="low", file_op=FACTOR_LOW_DEMAND_GENERIC),
           Scenario(f"{sector}_high", suffix="high", file_op=FACTOR_HIGH_DEMAND_GENERIC),
       ]

Pattern 3: read the variation from a source
-------------------------------------------

When the variation is not a factor but different data, the dataset builds the
``Scenario``, in a ``get_<attribute>_scenario()`` method next to its
``get_<attribute>()``. The rule that elements do not process data applies to
scenarios as well. ``Biomass`` reads the low and high potentials of ENSPRESO
this way:

.. code-block:: python

   def _set_availability_import(self) -> Attribute:
       """Return the import availability of biomass from ENSPRESO potentials."""
       enspreso = EnspresoBiomassAvailability(self.source_path)
       attr = enspreso.get_availability_import(
           element=self, biomass_types=self._biomass_types
       )
       if self.settings.scenario.sensitivity_biomass:
           attr.add_scenarios([
               enspreso.get_availability_import_scenario(
                   element=self, biomass_types=self._biomass_types,
                   name="biomass_low", ens_scenario="ENS_Low", suffix="low",
               ),
               enspreso.get_availability_import_scenario(
                   element=self, biomass_types=self._biomass_types,
                   name="biomass_high", ens_scenario="ENS_High", suffix="high",
               ),
           ])
       return attr

The dataset method returns the ``Scenario`` with the data of the other source
scenario, and reuses the same private computation as the default value:

.. code-block:: python

   def get_availability_import_scenario(
       self, element: Carrier, biomass_types: list[str],
       name: str, ens_scenario: str, suffix: str,
   ) -> Scenario:
       """Build a scenario variation of the import availability."""
       reference_year_values, yearly_variation = self._compute_availability_import(
           element=element, biomass_types=biomass_types, scenario=ens_scenario
       )
       return Scenario(
           name,
           suffix=suffix,
           df=reference_year_values,
           yearly_variations_df=yearly_variation,
       )

Scenarios of sets and settings
------------------------------

A scenario that changes one attribute of every technology or carrier is
registered in ``zen_europe/global_scenarios.py``, guided by the settings:

.. code-block:: python

   def define_global_scenarios(model: Model) -> None:
       """Register the system, analysis, solver, and set-wide scenarios."""
       if model.settings.scenario.sensitivity_no_diffusion_rate:
           model.scenarios.add_set(
               name="no_diffusion_rate",
               set_label="set_technologies",
               param="max_diffusion_rate",
               default_op=0.0,
           )

Set entries only take factors and names of files, since the registry does not
write data into the folder of each element. Use ``exclude`` to leave single
elements unchanged. ZEN-garden settings are varied in the same function with
``model.scenarios.add()``, or in the ``scenarios:`` block of the configuration
file (see :ref:`tutorials.tutorials`).

The full reference of the scenario classes is in the `ZEN-creator
documentation
<https://zen-creator.readthedocs.io/en/latest/files/quick_start/scenarios.html>`_.


