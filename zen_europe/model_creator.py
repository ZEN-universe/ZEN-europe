from pathlib import Path

from zen_creator import Model

from .datasets import (
    dataset_collections,  # noqa: F401
    datasets,  # noqa: F401
)

# import custom element classes to register them in the registry (side effect)
from .elements import (
    carriers,  # noqa: F401
    conversion_technologies,  # noqa: F401
    energy_systems,  # noqa: F401
    storage_technologies,  # noqa: F401
    transport_technologies,  # noqa: F401
)


def create_model(
    config: Path | str | None = None,
    name: str = "zen-europe",
    output_folder: Path | str = ".",
    write: bool = True,
) -> Model:
    # Get path to crystal ball model
    zen_europe_package_dir = Path(__file__).resolve().parent.parent
    crystal_ball_path = zen_europe_package_dir / "data" / "crystal_ball"

    if config is None:
        config = zen_europe_package_dir / "data" / "config.yaml"

    # load crystal ball model as starting point
    # TODO: this should be remove in the long run and replaced
    # with model.from_config()
    model = Model.from_existing(crystal_ball_path, config=config)
    model.output_folder = Path(output_folder)
    model.name = name

    # apply changes
    model.build()

    # =========================================================================
    # Fix Units for Non-Energy Technologies (Steel/Chemicals)
    # =========================================================================
    for tech_name, element in model.elements.items():
        # Sync Power / Base Units
        if hasattr(element, "capacity_lower_limit") and hasattr(element, "capacity_limit"):
            element.capacity_lower_limit.unit = element.capacity_limit.unit
            
        # Sync Energy Units for Storage
        if hasattr(element, "capacity_lower_limit_energy") and hasattr(element, "capacity_limit_energy"):
            element.capacity_lower_limit_energy.unit = element.capacity_limit_energy.unit

    # save model output
    if write:
        model.write()
        # =========================================================================
        # Post-write modifications & cleanup
        # =========================================================================
        print("\n--- Running Post-Write Actions ---")
        new_model_path = model.output_folder / model.name
        files_deleted = 0

        if new_model_path.exists():
            for file_path in new_model_path.rglob("capacity_limit_yearly_variation.csv"):
                try:
                    file_path.unlink()  
                    print(f"Deleted unneeded variation file: {file_path}")
                    files_deleted += 1
                except Exception as e:
                    print(f"Could not delete {file_path}: {e}")

    return model
