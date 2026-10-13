from pathlib import Path

from zen_creator import Model
from zen_creator.utils.settings import ModelSet, Settings

# import settings categories to register them in the registry (side effect)
from . import settings  # noqa: F401

# import custom element classes to register them in the registry (side effect)
from .elements.carriers import Biomass, Electricity  # noqa: F401
from .elements.conversion_technologies import Photovoltaics  # noqa: F401
from .elements.energy_systems import EnergySystemNuts0  # noqa: F401
from .elements.retrofitting_technologies import SMR_CCS  # noqa: F401
from .elements.sectors import ElectricitySector  # noqa: F401
from .elements.storage_technologies import PumpedHydro  # noqa: F401
from .elements.transport_technologies import PowerLine  # noqa: F401
from .global_scenarios import define_global_scenarios
from .settings.cache import set_active_cache_settings

# the data folder of the repository, which holds the configuration, the models
# file, the raw data and the generated datasets
DATA_PATH = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CONFIG_PATH = DATA_PATH / "zen_europe_config.yaml"
DEFAULT_OUTPUT_PATH = Path("data") / "created_models"


def default_models_path(config: Path | str) -> Path:
    """The models file that sits next to the given configuration file."""
    return Path(config).resolve().parent / "models.yaml"


def create_model(
    config: Path | str | None = None,
    models: Path | str | None = None,
    model_name: str | None = None,
    name: str = "zen-europe",
    output_folder: Path | str | None = None,
    write: bool = True,
) -> Model:
    """Generate a ZEN-europe dataset.

    Args:
        config: The configuration file to read. Defaults to
            data/zen_europe_config.yaml.
        models: The models file declaring the model variants. Defaults to
            models.yaml next to the configuration file. Only read when
            model_name is given.
        model_name: The variant in the models file to generate. Its settings
            patch is applied on top of the configuration file's settings,
            and the dataset is named after it.
        name: The name of the dataset, used when model_name is not given.
        output_folder: The directory the dataset is written to, together with
            the config.yaml that ZEN-garden is run with. Overrides the
            ``output.path`` setting when given.
        write: Whether to write the dataset to disk.
    """
    if config is None:
        config = DEFAULT_CONFIG_PATH

    patch = None
    if model_name is not None:
        model_set = ModelSet.load_from_yaml(models or default_models_path(config))
        patch = model_set.settings_patch(model_name)
        name = model_name

    model_settings = Settings.load_from_yaml(config, patch=patch)
    resolved_output_folder = output_folder or model_settings.output.path

    model = Model.from_config(config, settings=model_settings)
    set_active_cache_settings(model.settings.cache)
    model.output_folder = Path(resolved_output_folder)
    model.name = name

    # apply changes
    model.build()

    # register the system-, analysis-, solver-, and set-wide scenarios
    model.apply_global_scenarios(define_global_scenarios)

    # save model output
    if write:
        model.write()

    return model
