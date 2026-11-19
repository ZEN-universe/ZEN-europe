from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.datasets.financial.ECB import ECBInflation

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.carriers.carrier import Carrier
import pandas as pd
from zen_creator import Attribute, ConversionTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation

from zen_europe.utils.constants import Constants

# fuel consumption of the cement kiln routes (GJ/t clinker); hydrogen and waste are
# the alternative fuel mix
CEMENT_FUEL_CONSUMPTION = {
    "hard_coal": 2.13,
    "hydrogen": 2.46,
    "biomass": 2.77,
    "waste": 2.46,
}
# kiln fuel input per kiln fuel output of the glass routes, weighted by production
# share, relative to the natural gas route; also used for ceramic (see docs)
KILN_FUEL_INPUT = {"natural_gas": 1.0, "hydrogen": 1.0577, "electricity": 0.8438}
# share of the glass fuel demand that a fuel can cover at most: the glass routes run
# fully on natural gas, hydrogen or electricity (Tables 19, 21 and 23)
GLASS_FUEL_MAX_SHARE = {
    "natural_gas_to_glass_fuel": 1.0,
    "hydrogen_to_glass_fuel": 1.0,
    "electricity_to_glass_fuel": 1.0,
}
# capex of the glass routes minus the natural gas routes (EUR/t), weighted by
# production share (Tables 19, 21 and 23); small, so the retrofits have no capex
GLASS_ROUTE_CAPEX_DIFFERENCE = {
    "natural_gas_to_glass_fuel": 0.0,
    "hydrogen_to_glass_fuel": 1.5,
    "electricity_to_glass_fuel": -3.6,
}


class Aidres(Dataset[dict[str, pd.DataFrame]]):
    """
    Aidres dataset class.

    This class implements the specific behavior for the Aidres dataset.
    """

    name = "aidres"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Advancing industrial decarbonisation by assessing the "
                "future use of renewable energies in industrial processes"
            ),
            author=["Luc Girardin", "Juan Correa Laguna", "Joris Valee"],
            publication="Publications Office of the European Union",
            publication_year=2023,
            url="https://op.europa.eu/en/publication-detail/-/publication/d80943a6-5116-11ee-9220-01aa75ed71a1/language-en",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "industry"

    def _set_data(self) -> dict[str, pd.DataFrame]:
        prod_flow = pd.read_excel(
            self.path / "AIDRES_demand_database.xlsx",
            sheet_name="Product Flow",
            header=12,
        ).set_index("NUTS ID")
        cement_demand = prod_flow["Cement (kt/y)"]
        steel_demand = prod_flow["Steel (kt/y)"]
        methanol_sheet = pd.read_excel(
            self.path / "AIDRES_demand_database.xlsx",
            sheet_name="Methanol (PJ per y)",
            header=12,
        ).set_index("NUTS ID")
        methanol_demand = methanol_sheet["All sectors (PJ/y).1"]

        # glass routes (container, flat, fibre), Tables 19, 21 and 23
        glass = pd.read_csv(self.path / "AIDRES2023_glass.csv").set_index("sub_process")

        data = {
            "clinker": cement_demand.to_frame(name="demand"),
            "primary_steel": steel_demand.to_frame(name="demand"),
            "secondary_steel": steel_demand.to_frame(name="demand"),
            "methanol": methanol_demand.to_frame(name="demand"),
            "glass": glass,
        }
        return data

    # -------- methods ------------------------
    def get_demand(self, element: Carrier) -> pd.DataFrame:
        """
        Get the demand of cement, steel, or methanol from the Aidres dataset.

        This method retrieves the demand data for the
        specified carrier from the Aidres dataset
        and returns it as a pandas DataFrame.

        Args:
            element (Carrier): The carrier element for which to get the demand.

        Returns:
            A pandas DataFrame containing the demand data for the specified carrier.
        """
        data = self.data[element.name]
        common_countries = pd.Index(data.index).intersection(
            element.model.config.system.set_nodes
        )
        data = data.loc[common_countries]
        return data

    def get_CEM2_clinker_ratio(self) -> float:
        """
        Get the clinker to cement ratio from the Aidres dataset.

        This method retrieves the clinker to cement ratio from the Aidres dataset
        and returns it as a float.

        Returns:
            A float representing the clinker to cement ratio.
        """
        return 0.7

    def get_energy_density_methanol(self) -> float:
        """
        Get the energy density of methanol from the Aidres dataset.

        This method retrieves the energy density of methanol from the Aidres dataset
        and returns it as a float.

        Returns:
            A float representing the energy density of methanol in MWh/t.
        """
        return 20.1 / Constants.GJ_PER_MWH

    def get_conversion_factors_aidres(self, technology: str) -> dict[str, float]:
        """
        Get the conversion factors from the Aidres dataset.

        This method retrieves the conversion factors for various
        technologies and carriers from the Aidres dataset
        and returns them as a dictionary.

        Returns:
            A dictionary containing the conversion factors for various carriers.
        """
        conversion_factors = {
            "olefin_from_methanol": {
                "methanol": 49.01
                / (Constants.GJ_PER_MWH * 1000),  # GWh/t, Table 32 (MeOH) O
                "electricity": 0.66
                / (Constants.GJ_PER_MWH * 1000),  # GWh/t, Table 32 (MeOH) O
            },
            "olefin_from_naphtha": {
                "naphtha": 60.52
                / (Constants.GJ_PER_MWH * 1000),  # GWh/t, Table 32 (LN) O (REF)
                "electricity": 1.06
                / (Constants.GJ_PER_MWH * 1000),  # GWh/t, Table 32 (LN) O (REF)
            },
        }
        if technology not in conversion_factors:
            raise ValueError(
                f"Conversion factors for technology {technology} "
                f"are not available in the Aidres dataset."
            )
        return conversion_factors[technology]

    def get_capex_specific_olefin(self, element: ConversionTechnology) -> Attribute:
        """
        Get the specific capital expenditure (capex) for olefin from methanol
        technologies.

        The total capex comes from page 69
        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        capex_total = {
            "olefin_from_methanol": 173.4 * 1e6,  # Euro, MTO
            "olefin_from_naphtha": 1042.8 * 1e6,  # Euro, NTO
        }
        capacity = {
            "olefin_from_methanol": 33120,  # kg/h, MTO
            "olefin_from_naphtha": 125000,  # kg/h, NTO
        }
        money_year = {
            "olefin_from_methanol": 2013,  # MTO
            "olefin_from_naphtha": 2017,  # NTO
        }
        if element.name not in capex_total:
            raise ValueError(
                f"Capex data for technology {element.name} "
                f"are not available in the Aidres dataset."
            )
        capex_total_value = capex_total[element.name]
        capacity_value = capacity[element.name]
        capex_specific_value = capex_total_value / capacity_value * 1000  # Euro/(t/h)
        inflation = ECBInflation(source_path=self.source_path).get_inflation_rate(
            base_year=money_year[element.name],
            target_year=element.settings.time.price_year,
        )
        capex_specific_value *= inflation
        attr = element.capex_specific_conversion
        attr.set_data(
            default_value=capex_specific_value,
            unit="Euro/(tproduct/h)",
            source=SourceInformation(
                description=(
                    f"The specific capital expenditure (capex) for {element.name} "
                    "technologies is based on the work of Aidres et al. (2023)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_conversion_factor_cement_fuel(
        self, element: ConversionTechnology
    ) -> Attribute:
        """
        Get the conversion factor for cement fuel technologies from the Aidres dataset.

        This method retrieves the conversion factor for cement fuel technologies
        from the Aidres dataset and returns it as an Attribute object.

        Returns:
            An Attribute object containing the conversion factor for cement fuel
            technologies.
        """
        attr = element.conversion_factor
        consumption = CEMENT_FUEL_CONSUMPTION
        cf: dict[str, dict[str, float]] = {
            "hydrogen_to_cement_fuel": {
                "hydrogen": consumption["hydrogen"] / consumption["hard_coal"]
            },
            "biomass_to_cement_fuel": {
                "biomass": consumption["biomass"] / consumption["hard_coal"]
            },
            "waste_to_cement_fuel": {
                "waste": consumption["waste"] / consumption["hard_coal"]
            },
            "coal_to_cement_fuel": {"hard_coal": 1},
        }
        assert element.name in cf, f"Conversion factor for {element.name} not found."

        cf_car = [
            {cf_car_key: {"default_value": cf_car_value, "unit": "GW/GW"}}
            for cf_car_key, cf_car_value in cf[element.name].items()
        ]

        attr.set_data(
            default_value=cf_car,
            source=SourceInformation(
                description=(
                    "The conversion factor for cement fuel technologies is based"
                    " on the work of Aidres et al. (2023)."
                ),
                metadata=self.metadata,
            ),
        )
        return attr

    def get_share_capacity_existing_cement_fuel(self) -> dict[str, float]:
        """
        Get the share of existing capacity for cement fuel technologies from the Aidres
        dataset.

        This method retrieves the share of existing capacity for cement fuel
        technologies
        from the Aidres dataset.

        p. 47

        Returns:
            The share of existing capacity of each cement fuel technology.
        """
        existing_capacity_share = {
            "hydrogen_to_cement_fuel": 0.0,  # no existing capacity
            "biomass_to_cement_fuel": 0.16,  # 16% of existing capacity
            "waste_to_cement_fuel": 0.3,  # 30% of existing capacity
            "coal_to_cement_fuel": 0.54,  # 54% of existing capacity
        }
        return existing_capacity_share

    def get_sub_processes_glass(self) -> pd.DataFrame:
        """Natural gas and electricity intensity (GJ/t) per glass route."""
        return self.data["glass"][["ng_GJ_t", "elec_GJ_t"]]

    def get_production_shares_glass(self) -> pd.Series:
        """EU production share per glass route."""
        return self.data["glass"]["eu_production_share"]

    def get_process_emissions_glass(self) -> float:
        """
        Get the process (raw-material decomposition) CO2 of glass production, in t
        per t of glass.

        Returns:
            float: The direct emissions of the electric glass routes, which only emit
                process CO2, weighted by EU production share (Tables 19, 21 and 23).
        """
        glass = self.data["glass"]
        return float(glass["emit_elec"].dot(glass["eu_production_share"]))

    def get_max_fuel_share_glass(self, name: str) -> float:
        """Share of the glass fuel demand that the glass fuel retrofit `name` can
        cover at most."""
        if name not in GLASS_FUEL_MAX_SHARE:
            raise ValueError(f"Maximum glass fuel share of {name} is not defined.")
        return GLASS_FUEL_MAX_SHARE[name]

    def get_capex_specific_conversion_glass_fuel(
        self, element: ConversionTechnology
    ) -> Attribute:
        """No capex of the glass fuel retrofit `element`: the AIDRES capex of its
        routes is close to that of the natural gas routes."""
        if element.name not in GLASS_ROUTE_CAPEX_DIFFERENCE:
            raise ValueError(f"Capex difference of {element.name} is not defined.")
        difference = GLASS_ROUTE_CAPEX_DIFFERENCE[element.name]
        return element.capex_specific_conversion.set_data(
            default_value=0.0,
            unit="Euro/GW",
            source=SourceInformation(
                description=(
                    "No capex: the production-weighted capex of the glass routes "
                    f"differs from the natural gas routes by {difference:+.1f} EUR/t "
                    "(Tables 19, 21 and 23). This is optimistic (new furnace, shorter "
                    "campaigns, size limits)."
                ),
                metadata=self.metadata,
            ),
        )

    def get_conversion_factor_kiln_fuel(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Fuel input per kiln fuel, relative to the natural gas route."""
        return element.conversion_factor.set_data(
            default_value=[
                {
                    element.fuel: {
                        "default_value": KILN_FUEL_INPUT[element.fuel],
                        "unit": "GW/GW",
                    }
                }
            ],
            source=SourceInformation(
                description=(
                    "Fuel input per kiln fuel of the glass routes, relative to the "
                    "natural gas route, weighted by production share (Tables 19, 21 "
                    "and 23)."
                ),
                metadata=self.metadata,
            ),
        )
