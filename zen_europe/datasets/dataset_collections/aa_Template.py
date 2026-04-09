from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.datasets.datasets.dataset import Dataset
    from zen_creator.elements.element import Element

from zen_creator.datasets.dataset_collections.dataset_collection import (
    DatasetCollection,
)
from zen_creator.datasets.datasets import TemplateDataset
from zen_creator.utils.attribute import Attribute


class TemplateDatasetCollection(DatasetCollection):
    """
    Template class for dataset collections. This template is designed as a
    starting point for users wishing to implement a new dataset collection.
    Please read the docstrings and comments carefully for notes on how to use
    the template.

    A dataset collection groups multiple datasets and exposes methods that return
    Attribute objects for elements. Even when multiple datasets are available,
    data processing should primarily happen in dataset classes and this class
    should be used as a readable map to those datasets.

    All dataset collections must inherit from the DatasetCollection class and
    implement the required abstract methods. In this template, only one dataset
    (`TemplateDataset`) is used for demonstration purposes.

    All methods and properties that need to be implemented are marked with a
    `TODO` comment. You can search for `TODO` in this file to quickly find all
    places where you need to make changes.
    """

    name = "template_dataset_collection"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset]:
        """
        Return all datasets belonging to this collection.

        This method is used to set the self.data property when the dataset
        collection is constructed.

        `TODO`: This method must be implemented. It should return a dictionary
        where keys are dataset names and values are Dataset objects.
        """

        return {
            "template_dataset": TemplateDataset(self.source_path),
            # Add more datasets here if needed
            # "dataset2_name": Dataset2(),
            # "dataset3_name": Dataset3(),
        }

    def get_max_load(self, element: Element, **kwargs) -> Attribute:
        """
        Function for creating max_load attribute.

        Functions for other attributes should follow the same naming
        convention i.e. get_<attribute_name>.

        This function uses information from self.data and returns an object
        of class Attribute. Any internal functions which are called by this
        function should begin with an underscore to clearly mark them as
        internal.

        Additional keyword arguments can be added to the function signature if
        needed. These can be helpful if the dataset collection has multiple
        configurations and/or settings which control the result.
        """
        dataset = self.data["template_dataset"]

        # validate to ensure dataset is correct type
        if not isinstance(dataset, TemplateDataset):
            raise TypeError(
                "Expected 'template_dataset' entry to be a TemplateDataset, got "
                f"{type(dataset).__name__}."
            )

        attr = dataset.get_max_load(element=element, **kwargs)
        return attr

    def _max_load_unit(self):
        """
        Helper function for creating the 'max_load' attribute.

        All helper functions should begin with an underscore to clearly mark
        them as internal.
        """
        return "MW"
