.. _dev_workflow.dev_workflow:

###########################
Developer Workflow
###########################

This guide describes the recommended workflow for creating and modifying
ZEN-garden input data with ``ZEN-creator``.

The typical process consists of three main phases:

1. Create a model object from an existing model folder.
2. Modify the model (attributes, elements, and optional custom data pipelines).
3. Write the model to disk.


Create a Model from Existing Input
==================================

Use ``Model.from_existing()`` to load an existing ZEN-garden input folder into
the structured ``Model`` object.

Minimal example::

	from pathlib import Path
	from zen_creator.model import Model

	existing_model_path = Path("./path/to/existing_model")
	model = Model.from_existing(existing_model_path=existing_model_path)

Optional: pass a custom config file if you want explicit control over inserted
or excluded sectors/elements during construction::

	config_path = Path("./config_existing_model.yaml")
	model = Model.from_existing(
		existing_model_path=existing_model_path,
		config=config_path,
	)

What happens internally:

1. A ``Model`` is created from config defaults (or your provided config).
2. ``energy_system`` attributes are overwritten from the existing model.
3. All configured model elements are overwritten from the existing model.


Modify the Model
================

After loading, you can modify the model in several ways.

Change scalar metadata (for output naming/path)
------------------------------------------------

Set a new output location and/or model name before writing::

	model.output_folder = Path("./outputs")
	model.name = "my_modified_model"


Add or remove elements
----------------------

Add known element classes by name (registered subclasses)::

	model.add_element_by_name("photovoltaics")

Remove elements by name::

	model.remove_element_by_name("photovoltaics")

You can also add sectors, which add all elements configured in the
corresponding ``Sector`` class::

	model.add_sector_by_name("heat")


Change element attributes
-------------------------

Each element exposes typed ``Attribute`` objects. You can modify their default
values and data using the element API and the ``Attribute`` helper methods.

Example pattern::

	heat_pump = model.elements["heat_pump"]
	heat_pump.max_load.set_data(default_value=1000, source="assumption")


Extend Data Processing with a New Dataset Subclass
==================================================

If you need new raw data preparation logic, implement a new subclass of the
abstract ``Dataset`` class.

Recommended implementation steps:

1. Create a new file under ``zen_creator/datasets/datasets/``.
2. Implement a subclass of ``Dataset`` and define class attribute ``name``.
3. Implement the required metadata/path/data hooks from the base class.
4. Perform raw data loading, cleaning, and transformation in this class.
5. Expose outward-facing helper methods (for example
   ``get_<attribute_name>()``) that return prepared values or ``Attribute``
   objects for element classes.
6. Add the new dataset import to
   ``zen_creator/datasets/datasets/__init__.py``.

Important convention:

- Keep all raw data handling in dataset classes.
- Keep element classes focused on mapping prepared data into model attributes.


Implement New Element Subclasses
================================

To add a new technology or carrier, create a subclass of the corresponding
element base class:

- ``Carrier``
- ``ConversionTechnology``
- ``StorageTechnology``
- ``TransportTechnology``
- ``RetrofittingTechnology``

Recommended implementation steps:

1. Add a new Python file in the corresponding folder under
   ``zen_creator/elements/``.
2. Implement a subclass with a unique ``name``.
3. Override relevant ``_set_<attribute_name>()`` methods to define default
   values and/or data-driven attributes.
4. Add the class import to the folder's ``__init__.py`` so that the subclass
   is loaded and available to the registry.
5. If the element should be automatically included through a sector, also add
   it to the matching ``Sector`` definition in ``zen_creator/sectors.py``.


Build and Apply Overwrites
==========================

When custom element subclasses define ``_set_<attribute_name>()`` methods,
calling ``Model.build()`` applies those subclass-defined values to the current
model object.

In other words, ``build()`` executes each element's build logic and updates
attribute defaults according to your subclass implementations.

Example::

	model.build()


Write the Final Model
=====================

Use ``Model.write()`` to validate and serialize the final model to disk.

Example::

	model.write()

``Model.write()`` performs the following:

1. Validates model consistency.
2. Removes existing output directory contents (if the target exists).
3. Writes ``system.json``.
4. Writes the ``energy_system`` folder.
5. Writes all carrier and technology folders.


End-to-End Example
==================

::

	from pathlib import Path
	from zen_creator.model import Model

	# 1) Load existing model
	model = Model.from_existing(Path("./existing_model"))

	# 2) Modify model
	model.output_folder = Path("./outputs")
	model.name = "scenario_with_custom_changes"

	# Optional: add/remove elements or adjust attributes
	# model.add_element_by_name("my_new_technology")
	# model.elements["heat_pump"].max_load.set_data(default_value=1200)

	# 3) Rebuild to apply subclass-specific _set_ logic
	model.build()

	# 4) Validate and write files
	model.write()


Checklist for Extensions
========================

Before running ``model.write()``, verify:

1. New datasets are implemented as ``Dataset`` subclasses.
2. Raw data processing is contained in dataset classes.
3. New carriers/technologies are implemented as proper element subclasses.
4. New classes are imported in the corresponding ``__init__.py`` files.
5. Optional sector wiring in ``zen_creator/sectors.py`` is updated if needed.
6. ``model.build()`` has been run after code-level changes to ``_set_`` logic.
7. Output location (``model.output_folder``) and model name are set as desired.

