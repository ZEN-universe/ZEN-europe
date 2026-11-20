from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from zen_creator import Attribute, DatasetCollection
from zen_creator.datasets.datasets.metadata import SourceInformation

from zen_europe.datasets.dataset_collections.clinker_data import ClinkerData
from zen_europe.datasets.dataset_collections.food_production_data import (
    FoodProductionData,
)
from zen_europe.datasets.dataset_collections.paper_production_data import (
    PaperProductionData,
)
from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.carrier.material_economics import MaterialEconomics
from zen_europe.datasets.datasets.carrier.seenergies_industrial_waste_heat import (
    SeenergiesIndustrialWasteHeat,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.agora_industry_steel import (
    AgoraIndustrySteel,
)
from zen_europe.utils.constants import Constants
from zen_europe.utils.industry import waste_heat_carrier

if TYPE_CHECKING:
    from zen_creator import Dataset, Element
    from zen_creator.utils.settings import Settings


class IndustrialWasteHeat(DatasetCollection):
    """Recoverable waste heat of the industrial processes (sEEnergies): the
    conversion factor of each process plus its waste heat per energy input."""

    name = "industrial_waste_heat"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Dataset[Any] | DatasetCollection]:
        """Load all available data sources."""
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "seenergies_industrial_waste_heat": SeenergiesIndustrialWasteHeat(
                self.source_path
            ),
            "aidres": Aidres(self.source_path),
            "clinker_data": ClinkerData(self.source_path),
            "paper_production_data": PaperProductionData(
                self.settings, self.source_path
            ),
            "food_production_data": FoodProductionData(self.settings, self.source_path),
            "agora_industry_steel": AgoraIndustrySteel(self.source_path),
            "dea": DEA(source_path=self.source_path),
            "material_economics": MaterialEconomics(source_path=self.source_path),
        }

    # ---------- conversion factors with waste heat ----------

    def get_conversion_factor_kiln_fuel(self, element: Element) -> Attribute:
        """Get the AIDRES fuel input per kiln fuel plus the waste heat of the glass
        furnaces per fuel input; glass is the proxy for the ceramic kilns."""
        attr = cast(Aidres, self.data["aidres"]).get_conversion_factor_kiln_fuel(
            element
        )
        proxy = (
            " Glass is the proxy for the ceramic kilns."
            if element.sector == "ceramic"
            else ""
        )
        return self._add_waste_heat(
            element,
            attr,
            self._seenergies.get_waste_heat_share_glass(),
            [element.fuel],
            "of the fuel input of a regenerative glass furnace: the difference "
            f"between the exhaust without and with batch/cullet preheating.{proxy}",
        )

    def get_conversion_factor_cement_production(self, element: Element) -> Attribute:
        """Get the conversion factor of the cement kilns plus their waste heat per
        cement fuel input."""
        attr = cast(
            ClinkerData, self.data["clinker_data"]
        ).get_conversion_factor_cement_production(element)
        return self._add_waste_heat(
            element,
            attr,
            self._seenergies.get_waste_heat_share_cement(),
            ["cement_fuel"],
            "of the cement fuel input of a dry cement kiln with preheater.",
        )

    def get_conversion_factor_cement_post_comb(self, element: Element) -> Attribute:
        """Get the DEA conversion factor of the cement capture. Its heat output
        includes the pre-cooling of the kiln flue gas, so the kiln exhaust heat that
        cement_production already outputs is subtracted per captured CO2."""
        dea = cast(DEA, self.data["dea"])
        attr = element.conversion_factor.set_data(
            default_value=dea.get_conversion_factor_cement_post_comb(),
            source=SourceInformation(
                description=(
                    "The conversion factor of cement post-combustion capture "
                    "is a manually derived value based on the DEA technology "
                    "catalogue for carbon capture, transport and storage "
                    "(Post-combustion carbon capture in a cement plant), "
                    "assuming the cement fuel input is directly converted "
                    "into heat for the capture process."
                ),
                metadata=dea.metadata,
            ),
        )
        if not waste_heat_carrier(element):
            return attr
        material_economics = cast(MaterialEconomics, self.data["material_economics"])
        share = self._seenergies.get_waste_heat_share_cement()
        fuel = material_economics.get_fuel_consumption_cement_kiln()  # GJ/t clinker
        intensity = material_economics._CARBON_INTENSITY_CEMENT_KILN  # tCO2/t clinker
        captured = intensity * dea.get_capture_rate_CCS()  # tCO2/t clinker
        kiln_heat = share * fuel / captured / Constants.GJ_PER_MWH  # MWh/tCO2
        conversion_factor = []
        for entry in attr.default_value:
            ((carrier, values),) = entry.items()
            if carrier == "recoverable_waste_heat":
                heat = round(values["default_value"] - kiln_heat, 12)
                values = {**values, "default_value": heat}
            conversion_factor.append({carrier: values})
        return attr.set_data(
            default_value=conversion_factor,
            source=SourceInformation(
                description=(
                    "The DEA heat output includes the pre-cooling of the kiln flue "
                    "gas (note I) and the kiln waste heat recovery units (notes A, "
                    "M), so the kiln exhaust heat that cement_production already "
                    f"outputs is subtracted: {share:.0%} of {fuel} GJ/t clinker per "
                    f"{captured:.3f} tCO2 captured per t clinker = {kiln_heat:.3f} "
                    "MWh/tCO2."
                ),
                metadata=self.metadata,
            ),
        )

    def get_conversion_factor_paper_production(self, element: Element) -> Attribute:
        """Get the energy demand per tonne of paper plus the waste heat per total
        energy input."""
        attr = cast(
            PaperProductionData, self.data["paper_production_data"]
        ).get_conversion_factor(element)
        return self._add_waste_heat(
            element,
            attr,
            self._seenergies.get_waste_heat_paper(),
            self._carriers(attr),
            "of the total energy input of board and packaging paper making: the "
            "difference between boilers without and with heat recovery.",
        )

    def get_conversion_factor_food_production(self, element: Element) -> Attribute:
        """Get the energy demand per tonne of food plus the waste heat per total
        energy input, with paper as the proxy."""
        attr = cast(
            FoodProductionData, self.data["food_production_data"]
        ).get_conversion_factor(element)
        return self._add_waste_heat(
            element,
            attr,
            self._seenergies.get_waste_heat_paper(),
            self._carriers(attr),
            "of the total energy input of board and packaging paper making: the "
            "difference between boilers without and with heat recovery. Paper is "
            "the proxy for food.",
        )

    def get_conversion_factor_steel(self, element: Element) -> Attribute:
        """Get the Agora conversion factor of a steel route plus its waste heat per
        tonne of steel. sEEnergies gives the waste heat per fuel of the blast stove
        or the EAF only, so it is not scaled by the Agora input of the route."""
        attr = cast(
            AgoraIndustrySteel, self.data["agora_industry_steel"]
        ).get_conversion_factor(element)
        waste_heat = self._seenergies.get_waste_heat_steel()[element.name]
        processes = {
            "BF_BOF": "the blast stove exhaust and the BOF off-gases: the difference "
            "between the exhaust without and with heat recovery. The coke ovens are "
            "not included.",
            "EAF": "the EAF: the difference between the exhaust without and with "
            "heat recovery.",
        }
        process = processes.get(
            element.name,
            f"{processes['EAF']} The DRI process has no data; the EAF is the proxy.",
        )
        return self._append_waste_heat(
            element,
            attr,
            waste_heat / (Constants.GJ_PER_MWH * 1000),
            "GWh/tproduct",
            f"The recoverable waste heat (cooling the exhaust to 55 °C) is "
            f"{waste_heat:.3f} GJ per tonne of steel from {process}",
        )

    # ---------- helpers ----------

    @property
    def _seenergies(self) -> SeenergiesIndustrialWasteHeat:
        return cast(
            SeenergiesIndustrialWasteHeat,
            self.data["seenergies_industrial_waste_heat"],
        )

    @staticmethod
    def _carriers(attr: Attribute) -> list[str]:
        """All carriers of the conversion factor `attr`."""
        return [carrier for entry in attr.default_value for carrier in entry]

    def _add_waste_heat(
        self,
        element: Element,
        attr: Attribute,
        share: float,
        carriers: list[str],
        description: str,
    ) -> Attribute:
        """Add the waste heat `share` of the input of `carriers` to the conversion
        factor `attr`, if industrial waste heat is used."""
        flows = {
            carrier: values
            for entry in attr.default_value
            for carrier, values in entry.items()
        }
        units = {flows[carrier]["unit"] for carrier in carriers}
        assert len(units) == 1, f"The inputs {carriers} have different units {units}."
        energy_input = sum(flows[carrier]["default_value"] for carrier in carriers)
        return self._append_waste_heat(
            element,
            attr,
            share * energy_input,
            units.pop(),
            f"The recoverable waste heat (cooling the exhaust to 55 °C) is "
            f"{share:.0%} {description}",
        )

    def _append_waste_heat(
        self,
        element: Element,
        attr: Attribute,
        waste_heat: float,
        unit: str,
        description: str,
    ) -> Attribute:
        """Append the waste heat to the conversion factor `attr`, if industrial waste
        heat is used."""
        if not waste_heat_carrier(element):
            return attr
        entry = {"default_value": round(waste_heat, 12), "unit": unit}
        return attr.set_data(
            default_value=[*attr.default_value, {"recoverable_waste_heat": entry}],
            source=SourceInformation(description=description, metadata=self.metadata),
        )
