from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

# price year of the JRC-EU-TIMES cost parameters
BASE_YEAR = 2006
# row of the column labels in the IND sheet
HEADER_ROW = 4
PARAMETERS = ["INVCOST", "FIXOM", "VAROM", "LIFE"]


class JRCEUTIMESIndustry(Dataset[pd.DataFrame]):
    """
    JRC-EU-TIMES industry dataset class.

    Costs, lifetimes and process emissions of industrial production processes.
    """

    name = "jrc_eu_times_industry"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="JRC-EU-TIMES model, industry technologies",
            author=["European Commission, Joint Research Centre"],
            publication="JRC-EU-TIMES",
            publication_year=2019,
            doi="10.2790/97596",
            note=(
                "JRC_EU_TIMES_model_input.xls (2019.11), sheet IND. The DOI is the "
                "one of the model description (2013)."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "03-technology"
            / "industry"
            / "JRC_EU_TIMES_model_input.xls"
        )

    def _set_data(self) -> pd.DataFrame:
        sheet = pd.read_excel(self.path, sheet_name="IND", header=None)
        sheet.columns = sheet.iloc[HEADER_ROW]
        sheet = sheet.iloc[HEADER_ROW + 1 :]
        # a process spans several rows, only the first one holds its name
        technology = sheet["TechName"].replace("", None).ffill()
        parameters = sheet[PARAMETERS]
        parameters = parameters.apply(
            lambda column: pd.to_numeric(
                column.astype(str).str.strip(), errors="coerce"
            )
        )
        # zeros are placeholders; a process takes its last non-zero value
        parameters = parameters.where(parameters != 0)
        parameters = parameters.groupby(technology.to_numpy()).last()
        parameters.index.name = "technology"
        return parameters.fillna(0.0)

    def get_process_parameters(self, technology: str) -> pd.Series:
        """
        Get the parameters of a process.

        Args:
            technology (str): The JRC-EU-TIMES process name.

        Returns:
            pd.Series: Investment cost, fixed and variable O&M cost (in BASE_YEAR
                prices), lifetime and process emissions.
        """
        if technology not in self.data.index:
            raise ValueError(f"{technology!r} not found in JRC-EU-TIMES.")
        return self.data.loc[technology]
