.. _execution.execution:

###########################
Execution Procedure
###########################

This page describes what happens when a ZEN-europe dataset is generated, from
the command line call to the written ZEN-garden input folder.


Entry points
============

The command line interface is installed as ``zen-europe``. It can also be
called as a module:

.. code-block:: shell

   zen-europe
   python -m zen_europe

Both call :func:`zen_europe.model_creator.create_model`, which can also be
used directly from Python:

.. code-block:: python

   from zen_europe.model_creator import create_model

   model = create_model(output_folder="./data/created_models")


Command line options
====================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Meaning
   * - ``--config_path``
     - Configuration file. Default: ``data/zen_europe_config.yaml``.
   * - ``--models_path``
     - Models file that declares the variants. Default: ``models.yaml`` next to
       the configuration file, that is ``data/models.yaml``.
   * - ``--model <name>``
     - Generate one variant of the models file.
   * - ``--all``
     - Generate every variant of the models file.
   * - ``--jobs <n>``
     - With ``--all``: number of variants generated at the same time.
       Default: the number of CPUs, at most 4.
   * - ``--sequential``
     - With ``--all``: generate the variants one after another in the current
       process.
   * - ``--name <name>``
     - Name of the dataset when no variant is selected. Default:
       ``zen-europe``.
   * - ``--output_path``
     - Folder the datasets are written to, together with the ``config.yaml``
       that ZEN-garden is run with. Overrides the typed ``output.path`` setting.
       Default: ``data/created_models``.


Generating several variants
===========================

With ``--all``, the CLI generates every variant of the models file:

1. All variants are resolved first, so that a mistake in the models file is
   reported before any data is read.
2. Each variant is generated in its own Python process, up to ``--jobs`` at a
   time. The log of a variant is only shown when it fails. At the end, the
   CLI reports which variants failed.
3. If any variant sets a ``cache.overwrite_*`` flag, the variants are
   generated one at a time, so that two processes do not write the same cache
   file.

With ``--sequential``, the variants are generated one after another in the
current process, with the full log. This is easier to debug, but the
variants share the datasets that are already loaded: a dataset that is
constructed with the settings of the first variant keeps them for all later
variants.


Steps of a run
==============

The following steps are executed for every generated dataset.

1. Load the settings
--------------------

The ``settings:`` block of the configuration file is read. If a variant is
selected, its patch from the models file is merged into this block (see
:ref:`tutorials.models_file`). The result is validated against the settings
categories in ``zen_europe/settings/``. Every field that is not given keeps
its default. Unknown categories, unknown fields and values of the wrong type
raise an error.

2. Load the configuration
-------------------------

The remaining blocks of the configuration file (``source_path``, ``system``,
``analysis``, ``solver``, ``energy_system``, ``scenarios``, ...) are read into
a ZEN-creator ``Config``. A value that is controlled by a setting (for example
``system.set_nodes``, controlled by ``settings.region.set_nodes``) must not appear in
the configuration file, otherwise an error is raised.

3. Apply the settings to the configuration
------------------------------------------

Each settings category writes the values it controls into the configuration.
Examples:

- ``settings.region.set_nodes`` sets ``system.set_nodes``
- ``settings.time.reference_year`` and ``settings.time.interval_between_years`` set the
  corresponding system values, and ``optimized_years`` is derived from
  ``settings.time.last_year``
- ``settings.investment.allow_investment`` and 
  ``settings.investment.use_existing_capacities``
  set ``system.allow_investment`` and ``system.use_capacities_existing``
- ``settings.structure.*`` selects the energy system, the sectors and the individual
  elements

4. Create the model structure
-----------------------------

``Model.from_config`` creates the model:

- the energy system class named in ``settings.structure.energy_system`` is
  instantiated
- the sectors in ``settings.structure.set_sectors`` are added. Each sector must find
  its required sectors in the same list. A technology declared by several
  sectors is only added when all of them are included.
- the elements listed individually in ``settings.structure.set_*`` are added
- the sectors in ``settings.structure.remove_sectors`` and then the elements in
  ``settings.structure.remove_technologies`` are removed

At this point the model knows which elements it contains, but no data has
been read yet.

5. Build the model
------------------

``model.build()`` builds the energy system first and then every element. For
each attribute that has a ``_set_<attribute>()`` method, the method is called
and its result becomes the attribute. The methods call datasets and dataset
collections, which are loaded on first use and reused afterwards. If an
attribute reads an attribute that has not been built yet (also of another
element), that attribute is built first.

The cache settings (``cache.overwrite_*``) are activated before the build.
They decide whether a downloaded source is read from its cached file in the
raw data folder or downloaded again.

6. Register the global scenarios
--------------------------------

``define_global_scenarios`` in ``zen_europe/global_scenarios.py`` adds
scenarios that are not tied to a single attribute: overrides of system,
analysis or solver settings and entries that apply to a whole set of
elements. Scenarios of a single attribute are registered during the build, in
the element that sets the attribute.

7. Validate and write
---------------------

``model.write()`` validates the model and writes it:

- every carrier used by a technology must exist in the model, and the
  reference carrier of a conversion technology must be one of its input or
  output carriers
- every scenario must refer to an element of the model

If the dataset folder already exists, its content is deleted first.


Output
======

The datasets are written to ``<output_path>``, by default
``data/created_models``:

.. code-block:: text

   data/created_models/
     config.yaml                     ZEN-garden configuration
     <dataset name>/
       system.yaml
       scenarios.yaml                 only if scenarios are defined
       energy_system/
         attributes.yaml
         base_units.yaml
         unit_definitions.txt
         set_nodes.csv
         set_edges.csv
         ...
       set_carriers/
         <carrier>/
           attributes.yaml
           sources.md
           <attribute>.csv
       set_technologies/
         set_conversion_technologies/
           <technology>/
           set_retrofitting_technologies/
             <technology>/
         set_storage_technologies/
           <technology>/
         set_transport_technologies/
           <technology>/

- ``attributes.yaml`` holds the default value and unit of every attribute.
- ``<attribute>.csv`` holds time series and node, edge or year dependent
  values, ``<attribute>_yearly_variation.csv`` holds yearly variations.
- ``sources.md`` lists, for every attribute, the processing steps with their
  description and citations.
- ``attributes_<scenario>.yaml`` and ``<attribute>_<scenario>.csv`` hold the
  values of scenarios.
- ``config.yaml`` contains the ``analysis`` and ``solver`` settings of the
  configuration file and sets ``analysis.dataset`` to the name of the dataset
  written last. With ``--all`` it therefore names an arbitrary one of the
  generated datasets; select the one to run with ZEN-garden's ``--dataset``
  option. The configuration file of ZEN-europe is kept apart from it, at
  ``data/zen_europe_config.yaml``, and must not be located at
  ``<output_path>/config.yaml``.

The dataset is named after ``--name``, or after the variant when ``--model``
or ``--all`` is used.

