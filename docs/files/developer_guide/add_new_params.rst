.. _dev_workflow.add_new_params:

#########################################
Cookbook: Add a New Element Attribute
#########################################

This cookbook shows how to add a new attribute to an element class in
``ZEN-creator``.

It applies to these element types:

- ``ConversionTechnology``
- ``Carrier``
- ``StorageTechnology``
- ``TransportTechnology``
- ``RetrofittingTechnology``
- ``Technology``

The implementation pattern is the same across all of them.


When to Edit Which Class
========================

Choose the class where the attribute is conceptually owned:

- Add to ``Technology`` if all technologies should have it.
- Add to ``ConversionTechnology`` if only conversion technologies need it.
- Add to ``StorageTechnology`` if only storage technologies need it.
- Add to ``TransportTechnology`` if only transport technologies need it.
- Add to ``RetrofittingTechnology`` if only retrofitting technologies need it.
- Add to ``Carrier`` if it is a carrier-level property.

Rule of thumb: put shared attributes as high in the inheritance tree as
possible, but not higher.


Core Recipe (6 Steps)
=====================

Step 1: Register the attribute name in ``_subclass_attribute_names``
---------------------------------------------------------------------

In the target class ``__init__``, append the new key to
``self._subclass_attribute_names`` and ensure it is added to
``self._attribute_names``.

Why this matters:

- The attribute appears in the element's ``attributes`` mapping.
- It is included in serialization/writing logic that iterates over
  ``_attribute_names``.


Step 2: Initialize an ``Attribute`` object in default setup
-----------------------------------------------------------

In the class-specific default initializer (for example
``set_default_values_conversion_technology``), create the attribute with
``Attribute(...)``.

Typical fields:

- ``name``: key written to attributes files
- ``default_value``: default scalar/list
- ``unit``: unit string if relevant
- ``element=self``


Step 3: Add property getter and setter
--------------------------------------

Expose the attribute via a typed property:

- ``@property`` getter returning ``Attribute``
- Setter validating with ``self._validate_attribute(value)``

This preserves consistent typing and validation behavior.


Step 4: Decide if you need ``_set_<attribute>()`` hooks
-------------------------------------------------------

Use ``_set_<attribute>()`` methods when the value is subclass-specific or
depends on references to other elements.

If the attribute is a plain default value, direct initialization in the
default-values method is enough.


Step 5: Update concrete subclasses only when needed
---------------------------------------------------

If the new attribute is mandatory for all subclasses of an abstract base,
override or populate it in each concrete subclass where required.

Example: for conversion technologies, attributes like
``input_carrier``/``output_carrier`` are always subclass-defined.


Step 6: Validate by round-tripping a model
------------------------------------------

Recommended quick check:

1. Build/load a model.
2. Set the new attribute on one element.
3. Write the model.
4. Confirm the corresponding ``attributes.json`` contains the new key/value.


Worked Example: ``min_full_load_hours_fraction``
================================================

Your recent change in ``conversion_technology.py`` is the reference example.

1. Registered the new name in ``_subclass_attribute_names``.
2. Created the attribute in ``set_default_values_conversion_technology``.
3. Added getter/setter with validation.

Minimal pattern::

	class ConversionTechnology(Technology, ABC):
		def __init__(self, model: Model, power_unit: str = "MW"):
			super().__init__(model=model, power_unit=power_unit)

			self._attribute_names = list(self._attribute_names)
			self._subclass_attribute_names = [
				"capex_specific_conversion",
				"input_carrier",
				"output_carrier",
				"conversion_factor",
				"min_full_load_hours_fraction",
			]
			self._attribute_names.extend(self._subclass_attribute_names)

			self.set_default_values_conversion_technology()

		def set_default_values_conversion_technology(self):
			self.min_full_load_hours_fraction = Attribute(
				name="min_full_load_hours_fraction",
				default_value=0,
				element=self,
			)

		@property
		def min_full_load_hours_fraction(self) -> Attribute:
			return self._min_full_load_hours_fraction

		@min_full_load_hours_fraction.setter
		def min_full_load_hours_fraction(self, value: Attribute) -> None:
			self._validate_attribute(value)
			self._min_full_load_hours_fraction = value


Class-Specific Notes
====================

``Technology``
--------------

- Adding here makes the attribute available to conversion, storage,
  transport, and retrofitting technologies.
- Prefer this for truly cross-technology parameters.

``ConversionTechnology`` / ``StorageTechnology`` /
``TransportTechnology`` / ``RetrofittingTechnology``
-----------------------------------------------------

- Use these classes for family-specific attributes.
- Keep family-only keys out of ``Technology`` to avoid bloating unrelated
  element types.

``Carrier``
-----------

- Follow the same recipe: register name, initialize ``Attribute``, add
  getter/setter.
- Carrier attributes are written under ``set_carriers/<carrier>/attributes.json``.


Common Pitfalls
===============

1. Forgetting to add the name to ``_subclass_attribute_names``.
2. Defining a property but never initializing the underlying private variable.
3. Skipping ``self._validate_attribute(value)`` in the setter.
4. Choosing the wrong abstraction layer (for example adding a very
   specific key to ``Technology`` instead of a subclass).


Quick Checklist
===============

Before opening a PR, verify:

1. Attribute key is in ``_subclass_attribute_names`` (or base class list).
2. Default ``Attribute`` object is created in class initialization.
3. Getter/setter exist and setter validates type.
4. Any needed ``_set_<attribute>()`` logic is implemented.
5. Model write output contains the new key in the expected ``attributes.json``.