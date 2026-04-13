from pathlib import Path

from zen_creator import Model


def create_model(
    config: Path | str | None = None,
    name: str = "zen-europe",
    output_folder: Path | str = ".",
    write: bool = True,
) -> Model:

    # Get path to crystal ball model
    zen_europe_package_dir = Path(__file__).resolve().parent.parent
    crystal_ball_path = zen_europe_package_dir / "data" / "crystal_ball"

    # load crystal ball model as starting point
    # TODO: this should be remove in the long run and replaced
    # with model.from_config()
    model = Model.from_existing(crystal_ball_path, config=config)
    model.output_folder = Path(output_folder)
    model.name = name

    # apply changes
    model.build()

    # save model output
    if write:
        model.write()

    return model
