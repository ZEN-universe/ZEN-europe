from pathlib import Path

import pandas as pd
from zen_creator import Attribute, Dataset, Element, MetaData, SourceInformation


class Neumann2022TransmissionLosses(Dataset[pd.Series]):

    name: str = "neumann_2022_transmission_losses"

    def __init__(self, source_path: str | Path | None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Assessments of linear power flow and transmission loss "
                "approximations in coordinated capacity expansion problems"
            ),
            author=["Fabian Neumann", "Veit Hagenmeyer" "Tom Brown"],
            publication="Applied Energy",
            publication_year=2022,
            url="https://doi.org/10.1016/j.apenergy.2022.118859",
            doi="10.1016/j.apenergy.2022.118859",
            note=(
                "Page 7 of the PDF claims that `When using the lossy transport "
                "model, HVAC lines are assumed to have constant losses in the "
                "order of 5% per 1000 km`. They cite a document from Siemens "
                "when making this claim. This is therefore not a perfect primary"
                "source, but the numbers seems to generally agree with values "
                "in the literature."
            ),
        )

    def _set_path(self) -> None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series([0.00005], index=["power_line"])

    def get_transport_loss_factor_linear(self, element: Element) -> Attribute:

        if element.name not in self.data.index.values:
            raise ValueError(
                f"The dataset {self.name} does not contain loss factors for "
                f"the element {element.name}. Data is available for "
                f"{self.data.index.values}."
            )
        value = self.data.loc[element.name].item()
        if not isinstance(value, float):
            raise TypeError(
                f"Transmission loss for {element.name} must be a number "
                f"Expected `float`, got `{type(value)}`."
            )

        return Attribute(
            name="transport_loss_factor_linear",
            element=element,
            default_value=value,
            unit = "1/km",
            sources=[
                SourceInformation(
                    description=(
                        "Line losses are taken from the value stated in the "
                        "page 7 of the journal article. They reference a report"
                        "from Siemens when making the claim; however this report"
                        "is no longer accessible.`"
                    ),
                    metadata=self.metadata,
                )
            ],
        )
