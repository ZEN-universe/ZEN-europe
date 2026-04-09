################################
ZEN-Creator Class Structure
################################

Purpose
-------

The ``zen_creator`` package is built around a structured object model for
constructing, modifying, validating, and writing ZEN-garden input data.

The code is organized into clear layers, each with a specific job:

- ``Model`` orchestrates workflow and serialization.
- ``Element`` subclasses represent technologies, carriers, and the energy system.
- ``Attribute`` encapsulates default values, tabular data, units, and provenance.
- ``Dataset`` and ``DatasetCollection`` classes encapsulate raw data loading and
  transformation.


Core Architecture
-----------------

.. mermaid::
   :zoom:

   classDiagram
       class Model
       class Config
       class Sector
       class Element
       class EnergySystem
       class Attribute
       class Dataset
       class DatasetCollection

       Model --> Config
       Model --> Sector
       Model --> Element
       Model --> EnergySystem
       EnergySystem --|> Element
       Element --> Attribute
       DatasetCollection o-- Dataset
       Dataset ..> Attribute


Model Layer
-----------

``Model`` is the main coordinating class. It creates model objects from
configuration or existing model folders, applies updates, runs checks, and
writes output files.

.. mermaid::
   :zoom:

   classDiagram
       class Model {
           +name: str
           +config: Config
           +elements: dict[str, Element]
           +source_path: Path <<property>>
           +output_folder: Path <<property>>
           +output_path: Path <<property>>
           +energy_system: EnergySystem <<property>>
           +carriers: dict <<property>>
           +technologies: dict <<property>>
           +storage_technologies: dict <<property>>
           +conversion_technologies: dict <<property>>
           +transport_technologies: dict <<property>>
           +retrofitting_technologies: dict <<property>>
           +from_config() Model <<constructor>>
           +from_existing() Model <<constructor>>
           +add_sector_by_name() None
           +add_sector() None
           +remove_sector() None
           +add_element_by_name() None
           +add_element() None
           +remove_element() None
           +remove_element_by_name() None
           +build() None
           +validate() None
           +write() None
           +write_system_file() None
       }

       class Sector {
           +name: str <<class attribute>>
           +elements: list <<property>>
       }

       class Config

       Model --> Sector
       Model --> Config

Key methods:

- ``from_existing()``: load an existing ZEN-garden model folder and overwrite
  defaults with existing values.
- ``build()``: execute all element-specific ``_set_<attribute>()`` hooks to
  apply class-defined logic.
- ``validate()``: run consistency checks before writing.
- ``write()``: serialize ``system.json``, ``energy_system``, and all elements.


Element Layer
-------------

All physical model parts derive from ``Element``. ``Element`` provides shared
behavior for path handling, build logic, overwrite logic, and writing files.

.. mermaid::
   :zoom:

   classDiagram
       class Element {
           +name: str
           +subpath: str <<class variable>>
           +model: Model
           +config: Config
           +power_unit: str
           +source_path: Path <<property>>
           +relative_output_path: Path <<property>>
           +output_path: Path <<property>>
           +attributes: dict <<property>>
           +overwrite_from_existing_model() None
           +build() None
           +write() None
           +get_output_path() Path
           +attributes_to_dict() dict
           +save_attributes() None
           +save_data() None
       }

       class Attribute {
           +name: str
           +element: Element
           +default_value <<property>>
           +base_technology <<property>>
           +unit <<property>>
           +df <<property>>
           +yearly_variations_df <<property>>
           +source <<property>>
           +set_data() Attribute
           +overwrite_from_existing_model() None
           +default_to_dict() dict
           +save_data() None
       }

       Element --> Attribute

Key attributes and methods:

- ``Element.attributes``: the main map of all attributes that will be written.
- ``Element.build()``: automatically calls ``_set_<attribute_name>()`` when
  implemented by subclasses.
- ``Attribute.set_data()``: main method for setting defaults, units, data,
  yearly variations, and source metadata.
- ``Attribute.default_to_dict()`` and ``Attribute.save_data()``: convert values
  in memory into output files.


Energy System Class
-------------------

``EnergySystem`` is a specialized ``Element`` that stores global model settings
and network-level structures (nodes and edges).

.. mermaid::
   :zoom:

   classDiagram
       class EnergySystem {
           +price_carbon_emissions_annual_overshoot: Attribute <<property>>
           +carbon_emissions_budget: Attribute <<property>>
           +carbon_emissions_annual_limit: Attribute <<property>>
           +price_carbon_emissions_budget_overshoot: Attribute <<property>>
           +price_carbon_emissions: Attribute <<property>>
           +carbon_emissions_cumulative_existing: Attribute <<property>>
           +discount_rate: Attribute <<property>>
           +knowledge_spillover_rate: Attribute <<property>>
           +knowledge_depreciation_rate: Attribute <<property>>
           +market_share_unbounded: Attribute <<property>>
           +set_nodes: Attribute <<property>>
           +set_edges: Attribute <<property>>
           +set_default_values_energy_system() None
           +write() None
       }

       class Element
       EnergySystem --|> Element

Key behavior:

- Holds system-wide carbon, market, and learning assumptions.
- Manages graph-defining attributes ``set_nodes`` and ``set_edges``.
- Overrides ``write()`` to also write unit-related files in the
  ``energy_system`` folder.


Element Hierarchy
-----------------

Technology and carrier classes follow a simple inheritance hierarchy.

.. mermaid::
   :zoom:

   classDiagram
       class Element
       class Technology
       class Carrier
       class ConversionTechnology
       class StorageTechnology
       class TransportTechnology
       class RetrofittingTechnology

       <<abstract>> Element
       <<abstract>> Technology
       <<abstract>> ConversionTechnology
       <<abstract>> StorageTechnology
       <<abstract>> TransportTechnology
       <<abstract>> RetrofittingTechnology

       Element <|-- Technology
       Element <|-- Carrier
       Technology <|-- ConversionTechnology
       Technology <|-- StorageTechnology
       Technology <|-- TransportTechnology
       ConversionTechnology <|-- RetrofittingTechnology


Technology and Carrier APIs
---------------------------

The classes below define the most important technology and carrier attributes
that are commonly customized in subclasses.

.. mermaid::
   :zoom:

   classDiagram
       class Technology {
           +capacity_addition_min: Attribute <<property>>
           +capacity_addition_max: Attribute <<property>>
           +capacity_existing: Attribute <<property>>
           +capacity_limit: Attribute <<property>>
           +opex_specific_variable: Attribute <<property>>
           +opex_specific_fixed: Attribute <<property>>
           +construction_time: Attribute <<property>>
           +lifetime: Attribute <<property>>
           +reference_carrier: Attribute <<property>>
           +set_default_values_technology() None
           +_set_lifetime() Attribute*
           +_set_reference_carrier() Attribute*
       }

       class Carrier {
           +demand: Attribute <<property>>
           +availability_import: Attribute <<property>>
           +availability_export: Attribute <<property>>
           +price_import: Attribute <<property>>
           +price_export: Attribute <<property>>
           +carbon_intensity_carrier_import: Attribute <<property>>
           +carbon_intensity_carrier_export: Attribute <<property>>
           +price_shed_demand: Attribute <<property>>
           +set_default_values() None
       }

Key behavior:

- ``Technology`` defines the shared investment and operation attributes.
- ``Carrier`` defines demand, availability, prices, and carrier-specific carbon
  intensity attributes.
- Required abstract hooks in ``Technology`` ensure that every concrete
  technology class defines ``lifetime`` and ``reference_carrier``.


Technology Subclass APIs
------------------------

Each technology subtype adds a focused set of attributes and required hooks.

.. mermaid::
   :zoom:

   classDiagram
       class ConversionTechnology {
           +capex_specific_conversion: Attribute <<property>>
           +input_carrier: Attribute <<property>>
           +output_carrier: Attribute <<property>>
           +conversion_factor: Attribute <<property>>
           +set_default_values_conversion_technology() None
           +_set_input_carrier() Attribute*
           +_set_output_carrier() Attribute*
           +_set_conversion_factor() Attribute*
       }

       class StorageTechnology {
           +efficiency_charge: Attribute <<property>>
           +efficiency_discharge: Attribute <<property>>
           +self_discharge: Attribute <<property>>
           +capex_specific_storage: Attribute <<property>>
           +capex_specific_storage_energy: Attribute <<property>>
           +capacity_existing_energy: Attribute <<property>>
           +capacity_limit_energy: Attribute <<property>>
           +energy_to_power_ratio_min: Attribute <<property>>
           +energy_to_power_ratio_max: Attribute <<property>>
           +flow_storage_inflow: Attribute <<property>>
           +set_default_values_storage_technology() None
       }

       class TransportTechnology {
           +transport_loss_factor_linear: Attribute <<property>>
           +capex_per_distance_transport: Attribute <<property>>
           +distance: Attribute <<property>>
           +set_default_values_transport_technology() None
       }

       class RetrofittingTechnology {
           +retrofit_flow_coupling_factor: Attribute <<property>>
           +retrofit_reference_carrier: Attribute <<property>>
           +set_default_values_retrofitting_technology() None
           +_set_retrofit_flow_coupling_factor() Attribute*
           +_set_retrofit_reference_carrier() Attribute*
       }

Key behavior:

- ``ConversionTechnology`` enforces explicit carrier interfaces and conversion
  factors.
- ``StorageTechnology`` adds power-energy coupling and storage-specific
  efficiency/loss attributes.
- ``TransportTechnology`` focuses on distance-dependent losses and costs.
- ``RetrofittingTechnology`` extends conversion technologies with retrofit
  coupling attributes.


Data Layer
----------

Data classes separate raw data processing from element logic, so element
subclasses can stay focused on model behavior.

.. mermaid::
   :zoom:

   classDiagram
       class Dataset {
           +name: str
           +source_path: Path
           +title: str <<property>>
           +author: str <<property>>
           +publication: str <<property>>
           +publication_year: int <<property>>
           +doi: str <<property>>
           +url: str <<property>>
           +path: Path <<property>>
           +data <<property>>
           +metadata: dict <<property>>
           +_set_title() str*
           +_set_author() str*
           +_set_publication() str*
           +_set_publication_year() int*
           +_set_url() str*
           +_set_path() Path*
           +_set_data() *
           +get\_&lt;attribute_name&gt;() Attribute
       }

       class DatasetCollection {
           +name: str
           +source_path: Path
           +data: dict[str, Dataset] <<property>>
           +metadata: dict <<property>>
           +_get_data() dict[str, Dataset]*
       }

       class TechnoEconomicDataset {
           +available_technologies_finance: list
           +available_technologies_efficiency: list
           +available_technologies_lifetime: list
           +available_technologies_construction_time: list
           +money_year_source: int <<abstract_property>>
           +unit: str <<abstract_property>>
           +get_cost_data() DataFrame*
           +get_lifetime() DataFrame*
           +get_efficiency() DataFrame*
           +get_construction_time() DataFrame*
           +get_years() list[int]
           +get_units() str
           +rename_index() DataFrame
           +set_available_technologies() None
       }

       <<abstract>> Dataset
       <<abstract>> DatasetCollection
       <<abstract>> TechnoEconomicDataset

       DatasetCollection o-- Dataset
       Dataset <|-- TechnoEconomicDataset

Key behavior:

- ``Dataset`` defines strict metadata and data-loading hooks via ``_set_*``
  abstract methods.
- ``DatasetCollection`` groups multiple dataset objects and exposes aggregate
  metadata.
- ``TechnoEconomicDataset`` provides a common interface for finance,
  efficiency, lifetime, and construction-time data.


Workflow Perspective
--------------------

The main workflow across these classes is:

1. Create model object via ``Model.from_config()`` or ``Model.from_existing()``.
2. Add or remove sectors/elements on ``Model``.
3. Implement or adjust subclass ``_set_<attribute_name>()`` hooks.
4. Run ``Model.build()`` to apply class-defined defaults.
5. Run ``Model.write()`` to validate and serialize final model files.
