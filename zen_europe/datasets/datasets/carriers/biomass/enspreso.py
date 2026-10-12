from pathlib import Path

import pandas as pd
from zen_creator import (
    Attribute,
    Dataset,
    Element,
    MetaData,
    SourceInformation,
)

BIOMASS_TYPE_MAP = {
    "biomass": [
        "MINBIOAGRW1",
        # "MINBIOGAS1", # biogas
        # "MINBIOFRSR1a", # landscape residue, difficult to collect
        # "MINBIOCRP11", # energy crops
        # "MINBIOCRP21", # energy crops
        # "MINBIOCRP31", # energy crops
        # "MINBIOCRP41", # energy crops
        # "MINBIOCRP41a", # energy crops
        # "MINBIOLIQ1", # energy crops
        # "MINBIORPS1", # energy crops
        # "MINBIOFRSR1",
        "MINBIOFRSR1a",
        "MINBIOWOO",
        # "MINBIOWOOa",
        "MINBIOWOOW1",
        "MINBIOWOOW1a",
        "MINBIOMUN1",
        # "MINBIOSLU1",
    ],
    "wet_biomass": [
        "MINBIOGAS1",  # Manure solid, liquid
        "MINBIOSLU1",  # sludge
    ],
}

ALLOWED_SCENARIOS = [
    "ENS_Low",
    "ENS_Med",
    "ENS_High",
    "ENS_High_Forest400Mm3",
    "ENS_Med_ForestBaU",
    "ENS_Low_ForestBaU",
]


class ENSPRESO(Dataset[pd.DataFrame]):
    """
    ENSPRESO dataset for biomass availability.
    """

    name = "enspreso"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        """
        Return metadata for the ENSPRESO biomass dataset.
        """
        return MetaData(
            name=self.name,
            title="ENSPRESO - BIOMASS",
            author=["European Commission, Joint Research Centre"],
            publication="",
            publication_year=2026,
            url="http://data.europa.eu/89h/74ed5a04-7d74-4807-9eab-b94774309d9f",
            doi="10.2905/JRC.44AZBC8",
        )

    def _set_path(self) -> Path | None:
        """
        Return the path to the dataset file.

        This method is used to set the self.path property when the dataset is
        constructed.
        """
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")

        return self.source_path / "02-carrier" / "biomass" / "ENSPRESO"

    def _set_data(self) -> pd.DataFrame:
        """
        Load the dataset from self.path.

        Loads the ENSPRESO-BIOMASS excel spreadsheet for NUTS0 into a
        pandas DataFrame.
        """
        # can access self.path to load the dataset,
        data = pd.read_excel(
            self.path / "ENSPRESO_BIOMASS.xlsx", sheet_name="ENER - NUTS0 EnergyCom"
        )
        return data

    # -------- methods ------------------------

    def get_availability_import(self, element: Element) -> Attribute:

        scenario = self.get_scenario(element)
        biomass_types = BIOMASS_TYPE_MAP[element.name]
        biomass_potential: pd.DataFrame = self.data[
            (self.data["Scenario"] == scenario)
            & (self.data["Energy Commodity"].isin(biomass_types))
        ]
        biomass_potential = (
            biomass_potential.groupby(["NUTS0", "Year"]).sum()["Value"].unstack()
        )
        # convert PJ to GW
        biomass_potential = biomass_potential / 3.6 * 1000 / 8760

        # interpolate for all years between biomass_potential.columns.min() and
        # biomass_potential.columns.max()
        # ensure column labels are numeric years for correct range() use
        min_year: int = int(biomass_potential.columns.min())
        max_year: int = int(biomass_potential.columns.max())
        biomass_potential = biomass_potential.reindex(
            range(min_year, max_year + 1),
            axis=1,
        ).interpolate(axis=1)

        # extract only relevant nodes
        set_nodes = pd.Index(element.model.config.system.set_nodes)
        missing_nodes: pd.Index = set_nodes.difference(biomass_potential.index)
        if not missing_nodes.empty:
            raise ValueError(
                f"Warning: The following nodes are in the model but not in the "
                f"biomass potential dataset: {missing_nodes.tolist()}. "
                "The availability import for these nodes will be set to 0."
            )
        common_nodes = set_nodes.intersection(biomass_potential.index)
        biomass_potential = biomass_potential.loc[common_nodes]
        biomass_potential = biomass_potential.sort_index()

        # rename index
        biomass_potential.index.name = "node"

        # split into biomass_potential (per-node series) and
        # biomass_potential_yearly_variation (dataframe of relative changes)
        reference_year = element.model.config.system.reference_year
        biomass_potential_df: pd.DataFrame = biomass_potential.loc[:, reference_year:]
        biomass_potential_yearly_variation: pd.DataFrame = biomass_potential_df.div(
            biomass_potential_df[reference_year], axis=0
        )
        biomass_potential_series: pd.Series = biomass_potential_df[reference_year]
        biomass_potential_series.name = "availability_import"

        source_info = SourceInformation(
            description=(
                f"Biomass availability for {element.name} based on the "
                f"{scenario} scenario of the ENSPRESO dataset. "
                "The availability is calculated by summing availabilities in each "
                "year and NUTS0 region for the following biomass types: "
                f"{', '.join(biomass_types)}. "
                "The original units of the ENSPRESO database are PJ. The "
                "availability is converted to GW by assuming that biomass "
                "availability is spread evenly across the year. "
                "ENSPRESO reports the biomass potential in 10 year intervals. "
                "The biomass potential between these intervals is calculated "
                "by linear interpolation. "
            ),
            metadata=self.metadata,
        )
        attr = Attribute(
            name="availability_import",
            element=element,
            default_value=0,
            unit="GW",
            df=biomass_potential_series,
            yearly_variations_df=biomass_potential_yearly_variation,
            sources=[source_info],
        )
        return attr

    def get_scenario(self, element: Element) -> str:
        """
        Extract scenario from the carrier configurations.
        """
        element_name = element.name
        if not element.model.config.data.carrier.get(element_name, {}):
            raise ValueError(f"Missing configurations for carrier {element_name}.")
        element_config = element.model.config.data.carrier.get(element_name)

        # get scenario from the carrier configuration, raise error if not found
        scenario = getattr(element_config, "scenario", None)
        if scenario is None:
            raise ValueError(
                f"The configuration for carrier {element_name} does not "
                "have a setting named 'scenario' or is None."
            )
        if scenario not in ALLOWED_SCENARIOS:
            raise ValueError(
                f"The configuration for carrier {element_name} has an invalid"
                f"setting 'scenario': {scenario}. The scenario must be one of "
                f"{', '.join(ALLOWED_SCENARIOS)}"
            )
        return scenario
