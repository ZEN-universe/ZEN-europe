import numbers
from pathlib import Path

import pandas as pd

from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.elements.element import Element
from zen_creator.utils.attribute import Attribute


class TemplateDataset(Dataset[pd.DataFrame]):
    """
    Template class for datasets. This template is designed as a starting point
    for users wishing to implement a new dataset. Please read the
    docstrings and comments carefully for notes on how to use the template.

    All datasets must inherit from the Dataset class and implement the required abstract
    methods. These methods are called during the construction of the dataset object to
    set the author, title, publication, publication_year, url, path, and data properties
    of the dataset. Each of these methods is marked with a `TODO` comment to indicate
    that they must be implemented. You can search for `TODO` in this file to quickly
    find all the places where you need to make changes.

    The Dataset class takes a generic type parameter which specifies the
    return type of the data property. Please set this to the appropriate type
    for your dataset (e.g., pd.DataFrame, Dict[str, pd.DataFrame], etc.) and
    adjust the return type of _get_data() accordingly. In this template, we have set
    it to pd.DataFrame for demonstration purposes.

    All Datasets are singleton objects, meaning that they only get constructed once
    regardless of how many times they are instantiated. This is because datasets can be
    large and expensive to load, so we want to avoid loading them multiple times.
    The first time a dataset is instantiated, it will be constructed and loaded
    as normal. The second time it is instantiated, the existing instance will
    be returned instead of constructing a new one. This means that the constructor
    and the methods called during construction (i.e., the methods marked
    with `TODO` comments) will only be called once, even if the dataset is
    instantiated multiple times. This also means that the raw data only gets loaded
    once, and subsequent instantiations of the dataset will use the already loaded data.
    """

    name = "template_dataset"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_author(self) -> str:
        """
        Return the author(s) of the dataset.

        This method is used to set the self.author property when the
        dataset is constructed.

        `TODO`: This method must be implemented. It should return a string
        containing the name(s) of the author(s) of the dataset.
        """
        return "Reliability and Risk Engineering Lab"

    def _set_publication_year(self) -> int:
        """
        Return the publication year of the dataset.

        This method is used to set the self.publication_year property when the
        dataset is constructed.

        `TODO`: This method must be implemented. It should return an integer
        representing the publication year of the dataset.
        """
        return 2026

    def _set_title(self) -> str:
        """
        Return the title of the dataset.

        This method is used to set the self.title property when the
        dataset is constructed.

        `TODO`: This method must be implemented. It should return a string
        giving the title of the dataset.
        """
        return "Technology lifetimes and availability data for energy system modeling"

    def _set_publication(self) -> str:
        """
        Return the publication where the dataset was published.

        This method is used to set the self.publication property when the
        dataset is constructed.

        `TODO`: This method must be implemented. It should return a string
        giving the name of the publication.
        """
        return "Journal of Reliability and Risk Engineering"

    def _set_url(self) -> str:
        """
        Return the url from which the dataset was downloaded.

        This method is used to set the self.url property when the dataset is
        constructed.

        'TODO': This method must be implemented. It should return a string
        containing the url from which the dataset was downloaded.
        """
        return "https://example.com/dataset.csv"

    def _set_path(self) -> Path | None:
        """
        Return the path to the dataset file.

        This method is used to set the self.path property when the dataset is
        constructed.

        `TODO`: This method must be implemented. It should return a Path object
        pointing to the location of the dataset. It should use the self.source_path
        argument passed to the constructor to determine the location of the raw
        dataset files.
        """
        return Path(".")

    def _set_data(self) -> pd.DataFrame:
        """
        Load the dataset from self.path.

        This should be implemented to load the dataset from self.path and return
        it as a pandas DataFrame or a dictonary of pandas DataFrames. The exact
        implementation will depend on the format of the dataset (e.g., CSV, Excel,
        etc.) and the structure of the data. Any preprocessing steps (e.g.,
        handling missing values, renaming columns, etc.) should also be
        included in this method.

        The method is used to set the self.data property when the dataset is
        constructed. It therefore cannot take any inpyut arguments, but can
        access self.path and any other properties of the dataset.

        'TODO': This method must be implemented.
        """
        # can access self.path to load the dataset,
        # but here we will just return a dummy dataset for demonstration purposes
        data = pd.DataFrame(
            {"max_load": [100, 150, 200, 250], "availability_import": [1, 2, 3, 4]},
            index=[
                "template_conversion_technology",
                "template_storage_technology",
                "template_transport_technology",
                "template_retrofitting_technology",
            ],
        )

        return data

    # -------- methods ------------------------

    def get_max_load(self, element: Element, **kwargs) -> Attribute:
        """
        Function for creating max_load attribute.

        Functions for other attributes should follow the same naming
        convention i.e. get_<attribute_name>.

        This function uses information from self.data and returns an object
        of class Attribute. Any internal functions which are called by this
        function should begin with an underscore to clearly mark them as
        internal.

        Additional keyword arguments can be added to the function signature if needed.
        These can be helpful if, for example, the dataset has multiple configurations
        and/or settings which control the result. In this case, the relevant settings
        can be passed as keyword arguments to the function.
        """
        default_value = self.data.at[element.name, "max_load"]
        if not isinstance(default_value, numbers.Real):
            raise ValueError(
                "Expected numeric value for max_load, got type "
                f"{type(default_value).__name__}"
            )
        attr = Attribute("max_load", element)
        attr.set_data(
            default_value=float(default_value),
            unit=self._max_load_unit(),
            source=self.metadata,
        )
        return attr

    def _max_load_unit(self):
        """
        Helper function for creating the 'max_load' attribute.

        All helper functions should begin with an underscore to clearly mark them as
        internal.
        """
        return "MW"
